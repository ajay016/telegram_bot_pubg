from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status
from core.models import Product, Wallet, Order
from .serializers import *
from .utils.binance_client import binance_signed_request
from datetime import datetime, timedelta


# class ProductViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer
#     # permission_classes = [IsAuthenticated]

# class WalletViewSet(viewsets.ModelViewSet):
#     queryset = Wallet.objects.all()
#     serializer_class = WalletSerializer
#     # permission_classes = [IsAuthenticated]

# class OrderViewSet(viewsets.ModelViewSet):
#     queryset = Order.objects.all()
#     serializer_class = OrderSerializer
#     # permission_classes = [IsAuthenticated]


# ─── Category ────────────────────────────────────────────────────────────────

class CategoryList(APIView):
    def get(self, request):
        qs = Category.objects.all()
        serializer = CategorySerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetail(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk):
        obj = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(obj, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = get_object_or_404(Category, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── SubCategory ────────────────────────────────────────────────────────────

class SubCategoryList(APIView):
    def get(self, request):
        qs = SubCategory.objects.all()
        serializer = SubCategorySerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = SubCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubCategoryDetail(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(SubCategory, pk=pk)
        serializer = SubCategorySerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk):
        obj = get_object_or_404(SubCategory, pk=pk)
        serializer = SubCategorySerializer(obj, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = get_object_or_404(SubCategory, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# ─── Product ────────────────────────────────────────────────────────────────

class ProductList(APIView):
    def get(self, request):
        qs = Product.objects.all()
        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            # clean() will enforce category xor subcategory
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductDetail(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk):
        obj = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(obj, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = get_object_or_404(Product, pk=pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class WalletList(APIView):
    def get(self, request):
        wallets = Wallet.objects.all()
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = WalletSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WalletDetail(APIView):
    def get(self, request, pk):
        wallet = get_object_or_404(Wallet, pk=pk)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

    def put(self, request, pk):
        wallet = get_object_or_404(Wallet, pk=pk)
        serializer = WalletSerializer(wallet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        wallet = get_object_or_404(Wallet, pk=pk)
        serializer = WalletSerializer(wallet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        wallet = get_object_or_404(Wallet, pk=pk)
        wallet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrderList(APIView):
    def get(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrderDetail(APIView):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class PaymentMethodListView(APIView):
    """
    List all active payment methods.
    """

    def get(self, request):
        methods = PaymentMethod.objects.filter(is_active=True)
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentMethodDetailView(APIView):
    """
    Retrieve a payment method by ID and add `is_binance_pay` flag based on api_base_url.
    """

    def get(self, request, id):
        try:
            method = PaymentMethod.objects.get(id=id, is_active=True)
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Payment method not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PaymentMethodSerializer(method)
        data = serializer.data

        # Add Binance Pay check
        is_binance = "binance.com" in (data.get("api_base_url") or "")
        data["is_binance_pay"] = is_binance

        return Response(data, status=status.HTTP_200_OK)
    
    
class ConfirmTopUpView(APIView):
    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        if not transaction_id:
            return Response({"detail": "Missing transaction_id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = Transaction.objects.select_related("user").get(
                id=transaction_id,
                status="pending",
                transaction_type="topup",
                direction="credit",
            )
        except Transaction.DoesNotExist:
            return Response({"detail": "❌ Transaction not found or already processed."}, status=status.HTTP_404_NOT_FOUND)

        if transaction.is_expired():
            return Response({"detail": "⏰ This payment session has expired."}, status=status.HTTP_410_GONE)

        note = (transaction.note or '').strip()
        created_at = int(transaction.created_at.timestamp() * 1000 - 1000*60*60*72) 
        
        
        try:
            tx_data = binance_signed_request("/sapi/v1/pay/transactions", {"startTime": created_at, "limit": 50})
        except Exception as e:
            return Response({"detail": "❌ Binance API error."}, status=status.HTTP_502_BAD_GATEWAY)

        print('tx_data in api view: ', tx_data)
        if tx_data['message'].lower() == 'success':
            for tx in tx_data.get("data", []):
                remark = (tx.get("note") or '').strip() 
                if (
                    remark == note
                    and tx.get("currency") == "USDT"
                ):
                    amount = Decimal(tx["amount"])
                    wallet, _ = Wallet.objects.get_or_create(telegram_user=transaction.user)
                    wallet.balance += amount
                    wallet.save()

                    transaction.amount = amount
                    transaction.status = "confirmed"
                    transaction.save()
                    
                    if transaction.note:
                        note = transaction.note
                    else:
                        note = None
                    
                    PaymentTransaction.objects.create(
                        user=transaction.user,
                        wallet=wallet,
                        payment_method=transaction.payment_method,
                        topup_transaction=transaction,
                        amount=transaction.amount,
                        note=note,
                        status='completed',
                    )

                    BinancePayNote.objects.filter(note=note).update(is_used=True)

                    return Response({
                        "success": True,
                        "amount": f"{amount:.2f}",
                        "balance": f"{wallet.balance:.2f}",
                        "telegram_id": transaction.user.telegram_id,
                    })
        
        return Response({"detail": "❌ No matching Binance transaction found."}, status=status.HTTP_404_NOT_FOUND)

