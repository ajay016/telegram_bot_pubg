from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction
from django.core.paginator import Paginator
from django.contrib.admin.views.decorators import staff_member_required
import requests
from django.db.models import Sum, Q
import json
from .models import *
import logging










logger = logging.getLogger(__name__)



# Create your views here.
def home(request):
    return redirect('/admin/')


@staff_member_required(login_url='admin:login')
def dashboard(request):
    return render(request, 'core/test.html')


@staff_member_required(login_url='admin:login')
def upload_voucher_view(request):
    if request.method == 'POST':
        # 1. ADDED: Get the name from the form
        name = request.POST.get('name') 
        product_id = request.POST.get('product')
        supplier_id = request.POST.get('supplier')
        uploaded_file = request.FILES.get('file')

        # 2. ADDED: Validation for required and unique name
        if not name:
            return JsonResponse({
                'status': 'error', 
                'message': 'Upload Name is required.'
            }, status=400)
            
        if UploadVoucherCode.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                'status': 'error', 
                'message': 'An upload with this name already exists. Please choose a unique name.'
            }, status=400)

        # (Existing validation)
        if not product_id or not uploaded_file:
            return JsonResponse({
                'status': 'error', 
                'message': 'Product and File are strictly required.'
            }, status=400)
        
        if not uploaded_file.name.endswith('.txt'):
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid file format. Only .txt files are allowed.'
            }, status=400)

        try:
            product = Product.objects.get(id=product_id)
            supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
            
            # 3. MODIFIED: Include name=name in the object creation
            upload_obj = UploadVoucherCode(
                name=name,  # <- ADDED THIS LINE
                product=product,
                supplier=supplier,
                file=uploaded_file
            )
            upload_obj.clean() # Run custom model validations
            upload_obj.save()
            
            # Trigger file processing
            upload_obj.process_file()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Successfully uploaded and processed vouchers for {product.name}.'
            })
            
        except Exception as e:
            logger.error(f"Error processing voucher upload: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': f'An error occurred while processing the file: {str(e)}'
            }, status=500)

    # GET Request: Prepare data for the form dropdowns
    context = {
        'products': Product.objects.all(),
        'suppliers': Supplier.objects.all(),
    }
    return render(request, 'core/vouchers/upload_voucher.html', context)


@staff_member_required(login_url='admin:login')
def list_voucher_uploads_view(request):
    # Optimize query by fetching related product and supplier in one go
    uploads = UploadVoucherCode.objects.select_related('product', 'supplier').order_by('-uploaded_at')
    context = {
        'uploads': uploads
    }
    return render(request, 'core/vouchers/list_uploads.html', context)


@require_POST
def delete_voucher_upload_view(request, pk):
    try:
        upload = get_object_or_404(UploadVoucherCode, pk=pk)
        name = upload.name or "Unnamed Upload"
        upload.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted upload: {name}'
        })
    except Exception as e:
        logger.error(f"Error deleting upload {pk}: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while deleting the record.'
        }, status=500)


@staff_member_required(login_url='admin:login')
def voucher_upload_detail_view(request, pk):
    upload = get_object_or_404(UploadVoucherCode, pk=pk)
    
    # 1. Read the file to get the codes associated with this upload
    valid_codes = []
    try:
        if upload.file:
            upload.file.seek(0)
            lines = upload.file.read().decode('utf-8').splitlines()
            valid_codes = [line.strip() for line in lines if line.strip()]
    except Exception as e:
        logger.error(f"Error reading file for upload {pk}: {e}")

    # 2. Fetch the corresponding VoucherCode objects from the database
    voucher_codes = VoucherCode.objects.filter(product=upload.product, code__in=valid_codes)
    
    context = {
        'upload': upload,
        'voucher_codes': voucher_codes,
        'total_codes': voucher_codes.count(),
    }
    return render(request, 'core/vouchers/upload_detail.html', context)


@require_POST
def delete_voucher_codes_view(request):
    try:
        data = json.loads(request.body)
        code_ids = data.get('code_ids', [])
        product_id = data.get('product_id')

        if not code_ids:
            return JsonResponse({'status': 'error', 'message': 'No codes selected.'}, status=400)

        # Delete the specific voucher codes
        deleted_count, _ = VoucherCode.objects.filter(id__in=code_ids).delete()

        # Update the product stock since we removed vouchers
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            product.update_stock_from_vouchers()

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted {deleted_count} voucher code(s).'
        })
    except Exception as e:
        logger.error(f"Error deleting voucher codes: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while deleting the codes.'
        }, status=500)
        
        

@staff_member_required(login_url='admin:login')
def customer_balances_view(request):
    """Renders the base template for Customer Balances"""
    return render(request, 'core/customers/balances.html')


@require_GET
def customer_balances_data(request):
    """Handles Server-Side Processing for DataTables"""
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')
    
    # Ordering
    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    
    # Map DataTable column indices to model fields
    columns_map = {
        0: 'telegram_id',
        1: 'username',
        2: 'first_name',
        3: 'wallet__balance',
        4: 'created_at',
    }
    order_field = columns_map.get(order_column_index, 'created_at')
    if order_dir == 'desc':
        order_field = f'-{order_field}'

    # Base Queryset
    queryset = TelegramUser.objects.select_related('wallet').all()

    # Search Logic
    if search_value:
        queryset = queryset.filter(
            Q(telegram_id__icontains=search_value) |
            Q(username__icontains=search_value) |
            Q(first_name__icontains=search_value) |
            Q(last_name__icontains=search_value)
        )

    # Total records before/after filtering
    total_records = TelegramUser.objects.count()
    records_filtered = queryset.count()

    # Apply ordering and pagination (Slicing)
    queryset = queryset.order_by(order_field)[start:start+length]

    # Format Data for DataTable
    data = []
    for user in queryset:
        wallet_balance = user.wallet.balance if hasattr(user, 'wallet') else "0.000"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "N/A"
        
        data.append({
            'id': user.id, # Hidden, used for actions
            'telegram_id': user.telegram_id,
            'username': f"@{user.username}" if user.username else "N/A",
            'name': name,
            'balance': str(wallet_balance),
            'joined': user.created_at.strftime("%b %d, %Y"),
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': records_filtered,
        'data': data
    })


@require_GET
def customer_summary_view(request, pk):
    """Returns total deposits, spends, and available balance for a user"""
    user = get_object_or_404(TelegramUser, pk=pk)
    wallet_balance = user.wallet.balance if hasattr(user, 'wallet') else 0

    # Calculate Total Deposits (Credit Transactions)
    total_deposits = Transaction.objects.filter(
        user=user, direction='credit', status='confirmed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Calculate Total Spends (Debit Transactions)
    total_spends = Transaction.objects.filter(
        user=user, direction='debit', status='confirmed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    return JsonResponse({
        'balance': str(wallet_balance),
        'total_deposits': str(total_deposits),
        'total_spends': str(total_spends),
        'username': f"@{user.username}" if user.username else str(user.telegram_id)
    })



@require_POST
def edit_customer_view(request, pk):
    """Updates user details and wallet balance manually"""
    try:
        user = get_object_or_404(TelegramUser, pk=pk)
        data = json.loads(request.body)

        # Update User Details
        user.username = data.get('username', user.username)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()

        # Update or Create Wallet
        wallet, created = Wallet.objects.get_or_create(telegram_user=user)
        new_balance = data.get('balance')
        if new_balance is not None:
            wallet.balance = new_balance
            wallet.save()

            # Optional: You could create an 'adjustment' Transaction here to keep ledger intact
            # Transaction.objects.create(user=user, transaction_type='adjustment', amount=..., status='confirmed')

        return JsonResponse({'status': 'success', 'message': 'Customer updated successfully.'})
    except Exception as e:
        logger.error(f"Error updating customer {pk}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Failed to update customer.'}, status=500)



@require_POST
def delete_customer_view(request, pk):
    """Deletes a customer"""
    try:
        user = get_object_or_404(TelegramUser, pk=pk)
        user.delete() # Note: Wallet and Transactions are deleted via CASCADE
        return JsonResponse({'status': 'success', 'message': 'Customer deleted successfully.'})
    except Exception as e:
        logger.error(f"Error deleting customer {pk}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Failed to delete customer.'}, status=500)
    


@staff_member_required(login_url='admin:login')
@require_GET
def user_transactions_view(request, pk):
    """Renders the page to view a specific user's transactions"""
    user = get_object_or_404(TelegramUser, pk=pk)
    
    context ={
        'customer': user
    }
    return render(request, 'core/customers/user_transactions.html', context)



@require_GET
def user_transactions_data(request, pk):
    """Handles Server-Side Processing for the Transactions DataTable"""
    user = get_object_or_404(TelegramUser, pk=pk)
    
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')
    
    order_column_index = int(request.GET.get('order[0][column]', 5)) # Default to created_at
    order_dir = request.GET.get('order[0][dir]', 'desc')
    
    columns_map = {
        0: 'tx_id',
        1: 'transaction_type',
        2: 'direction',
        3: 'amount',
        4: 'status',
        5: 'created_at',
    }
    order_field = columns_map.get(order_column_index, 'created_at')
    if order_dir == 'desc':
        order_field = f'-{order_field}'

    queryset = Transaction.objects.filter(user=user)

    if search_value:
        queryset = queryset.filter(
            Q(tx_id__icontains=search_value) |
            Q(transaction_type__icontains=search_value) |
            Q(status__icontains=search_value) |
            Q(note__icontains=search_value)
        )

    total_records = Transaction.objects.filter(user=user).count()
    records_filtered = queryset.count()

    queryset = queryset.order_by(order_field)[start:start+length]

    data = []
    for tx in queryset:
        data.append({
            'id': tx.id,
            'tx_id': tx.tx_id or "N/A",
            'type': tx.get_transaction_type_display(),
            'direction': tx.get_direction_display(),
            'amount': str(tx.amount),
            'status': tx.get_status_display(),
            'date': tx.created_at.strftime("%b %d, %Y %H:%M"),
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': records_filtered,
        'data': data
    })



@require_GET
def transaction_details_view(request, tx_id):
    """Returns detailed JSON data for a specific transaction modal"""
    tx = get_object_or_404(Transaction, pk=tx_id)
    return JsonResponse({
        'tx_id': tx.tx_id or "N/A",
        'type': tx.get_transaction_type_display(),
        'direction': tx.get_direction_display(),
        'amount': str(tx.amount),
        'status': tx.get_status_display(),
        'note': tx.note or "None",
        'payment_method': tx.payment_method.name if tx.payment_method else "N/A",
        'order_id': tx.order.id if tx.order else "N/A",
        'date': tx.created_at.strftime("%b %d, %Y %H:%M:%S")
    })
    


@staff_member_required(login_url='admin:login')
def admin_pending_orders_view(request):
    return render(request, 'core/admin_orders/admin_pending_orders.html')



def admin_pending_orders_data(request):
    # DataTables Server-Side Processing
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    orders = Order.objects.filter(status="Admin Pending").select_related('user').order_by('-created_at')

    if search_value:
        orders = orders.filter(
            Q(id__icontains=search_value) | 
            Q(user__telegram_id__icontains=search_value) |
            Q(user__username__icontains=search_value)
        )

    paginator = Paginator(orders, length)
    page_number = (start // length) + 1
    page_obj = paginator.get_page(page_number)

    data = []
    for order in page_obj:
        # Assuming you want to show the first product name in the table
        first_item = order.items.first()
        product_name = first_item.product.name if first_item else "Unknown"
        qty = first_item.quantity if first_item else 0

        data.append({
            "id": order.id,
            "telegram_id": order.user.telegram_id,
            "username": order.user.username or "N/A",
            "product_name": product_name,
            "quantity": qty,
            "total_price": str(order.total_price),
            "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": orders.count(),
        "recordsFiltered": paginator.count,
        "data": data
    })



def order_details_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()
    
    items_data = [{
        "product_name": item.product.name,
        "quantity": item.quantity,
        "unit_price": str(item.unit_price),
        "total": str(item.quantity * item.unit_price)
    } for item in items]

    return JsonResponse({
        "order_id": order.id,
        "customer": order.user.telegram_id,
        "customer_username": order.user.username or "N/A",
        "status": order.status,
        "created_at": order.created_at.strftime("%b %d, %Y, %I:%M %p"),
        "total": str(order.total_price),
        "current_balance": str(order.user.wallet.balance), # ADD THIS LINE
        "items": items_data
    })
    


def send_telegram_notification(chat_id, text, uploaded_file=None):
    """Helper to send telegram message synchronously from Django View"""
    token = settings.TELEGRAM_BOT_TOKEN
    
    if uploaded_file:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        # Reset file pointer to the beginning after Django saved it!
        uploaded_file.seek(0) 
        files = {'document': (uploaded_file.name, uploaded_file.read())}
        data = {'chat_id': chat_id, 'caption': text, 'parse_mode': 'HTML'}
        try:
            response = requests.post(url, data=data, files=files)
            if response.status_code != 200:
                print(f"Telegram API Error (Document): {response.text}")
        except Exception as e:
            print(f"Telegram API Exception: {e}")
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        try:
            response = requests.post(url, data=data)
            if response.status_code != 200:
                print(f"Telegram API Error (Message): {response.text}")
        except Exception as e:
            print(f"Telegram API Exception: {e}")
            
            


def approve_order_api(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        
        if order.status != "Admin Pending":
            return JsonResponse({"status": "error", "message": "Order is not pending."})

        message = request.POST.get('message', 'Here is your requested order!')
        uploaded_file = request.FILES.get('file')

        with transaction.atomic():
            wallet = order.user.wallet  # Assuming OneToOne or ForeignKey relation
            
            # Final balance check before deducting
            if wallet.balance < order.total_price:
                return JsonResponse({"status": "error", "message": "Customer has insufficient balance. Cannot approve."})

            # Deduct balance
            wallet.balance -= order.total_price
            wallet.save()

            # Update Order
            order.status = "Completed"
            order.admin_response_text = message
            if uploaded_file:
                order.delivery_file = uploaded_file
            order.save()

        # Send to Telegram
        telegram_text = f"✅ <b>Order #{order.id} Approved!</b>\n\n{message}\n\n💰 <b>Remaining Balance:</b> ${wallet.balance}"
        send_telegram_notification(order.user.telegram_id, telegram_text, uploaded_file)

        return JsonResponse({"status": "success", "message": "Order approved & balance deducted."})




def reject_order_api(request, order_id):
    if request.method == "POST":
        data = json.loads(request.body)
        order = get_object_or_404(Order, id=order_id)
        
        reason = data.get('reason', 'No reason provided.')

        order.status = "Rejected"
        order.rejection_reason = reason
        order.save()

        # Notify User
        telegram_text = f"❌ <b>Order #{order.id} Rejected</b>\n\n<b>Reason:</b> {reason}\n<i>Your balance was not deducted.</i>"
        send_telegram_notification(order.user.telegram_id, telegram_text)

        return JsonResponse({"status": "success", "message": "Order rejected successfully."})




def delete_order_api(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        order.delete()
        return JsonResponse({"status": "success", "message": "Order deleted permanently."})