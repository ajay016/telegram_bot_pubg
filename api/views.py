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
    
    
    
class ConfirmBEP20TopUpView(APIView):
    def post(self, request):
        transaction_id = request.data.get("transaction_id")
        print(f"\n{'='*50}")
        print(f"[BEP20] Verification requested for transaction_id: {transaction_id}")

        if not transaction_id:
            return Response({"detail": "Missing transaction_id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tx = Transaction.objects.select_related("user").get(
                id=transaction_id,
                status="pending",
                transaction_type="topup",
                direction="credit",
            )
            print(f"[BEP20] Transaction found: id={tx.id}, amount={tx.amount}, status={tx.status}, created_at={tx.created_at}")
        except Transaction.DoesNotExist:
            print(f"[BEP20] ❌ Transaction not found or already processed for id={transaction_id}")
            return Response(
                {"detail": "❌ Transaction not found or already processed."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if tx.is_expired():
            print(f"[BEP20] ❌ Transaction {transaction_id} is expired.")
            BEP20ActiveAmount.objects.filter(amount=tx.amount).delete()
            return Response({"detail": "⏰ This payment session has expired."}, status=status.HTTP_410_GONE)

        amount = tx.amount
        # created_at_ms = int(tx.created_at.timestamp() * 1000 - 1000 * 60 * 60 * 72)
        # Search deposits only after payment session started
        # subtract 2 minutes buffer for safety
        created_at_ms = int(tx.created_at.timestamp() * 1000) - (1000 * 60 * 2)
        # Current time
        end_time_ms = int(timezone.now().timestamp() * 1000)
        print(f"[BEP20] tx.created_at = {tx.created_at}")
        print(f"[BEP20] created_at_ms = {created_at_ms}")
        print(
            f"[BEP20] Looking for deposits AFTER session start "
            f"— amount={amount}, startTime={created_at_ms}"
        )

        try:
            params = {
                "coin": "USDT",
                "startTime": created_at_ms,
                "endTime": end_time_ms,
                "limit": 100,
            }

            print(f"[BEP20] Request params => {params}")
            
            deposit_data = binance_signed_request(
                "/sapi/v1/capital/deposit/hisrec",
                params,
            )

            print(f"[BEP20] Binance response type before parsing: {type(deposit_data)}")
            print(f"[BEP20] Raw Binance API response: {deposit_data}")
        except Exception as e:
            print(f"[BEP20] ❌ Binance API exception: {e}")
            return Response({"detail": "❌ Binance API error."}, status=status.HTTP_502_BAD_GATEWAY)

        print(f"[BEP20] Raw Binance API response type: {type(deposit_data)}")
        print(f"[BEP20] Raw Binance API response: {deposit_data}")

        # Handle both raw list and dict-wrapped responses
        if isinstance(deposit_data, list):
            deposit_list = deposit_data
        elif isinstance(deposit_data, dict):
            # Try common Binance wrapper keys
            deposit_list = (
                deposit_data.get("data")
                or deposit_data.get("depositList")
                or []
            )
        else:
            deposit_list = []

        print("\n" + "=" * 80)
        print("[BEP20] ALL DEPOSITS RETURNED FROM BINANCE")
        print("=" * 80)

        for i, deposit in enumerate(deposit_list):
            print(f"\n[BEP20] Deposit [{i}] FULL DATA:")
            print(deposit)

        print("\n" + "=" * 80)
        print("[BEP20] STARTING MATCH CHECK")
        print("=" * 80)

        for i, deposit in enumerate(deposit_list):
            dep_amount = deposit.get("amount", "0")
            dep_status = deposit.get("status")
            dep_txid = deposit.get("txId", "")
            dep_insert_time = deposit.get("insertTime")
            dep_coin = deposit.get("coin")
            dep_network = deposit.get("network")
            dep_address = deposit.get("address")

            print(
                f"[BEP20] Deposit [{i}] => "
                f"amount={dep_amount}, "
                f"status={dep_status}, "
                f"txId={dep_txid}, "
                f"insertTime={dep_insert_time}, "
                f"coin={dep_coin}, "
                f"network={dep_network}, "
                f"address={dep_address}"
            )

            if dep_status != 1:
                print(f"[BEP20]   ↳ Skipped — status {dep_status} is not 1 (success)")
                continue

            if Decimal(str(dep_amount)) != amount:
                print(f"[BEP20]   ↳ Skipped — amount {dep_amount} != expected {amount}")
                continue

            print(f"[BEP20] ✅ Matching deposit found! txId={dep_txid}, amount={dep_amount}")

            if dep_txid and PaymentTransaction.objects.filter(tx_id=dep_txid).exists():
                print(f"[BEP20] ❌ Already processed txId={dep_txid}")
                return Response(
                    {"detail": "❌ This transaction has already been processed."},
                    status=status.HTTP_409_CONFLICT,
                )

            wallet, _ = Wallet.objects.get_or_create(telegram_user=tx.user)
            wallet.balance += amount
            wallet.save()
            print(f"[BEP20] Wallet updated — new balance: {wallet.balance}")

            tx.status = "confirmed"
            if dep_txid:
                tx.tx_id = dep_txid
            tx.save()

            PaymentTransaction.objects.create(
                user=tx.user,
                wallet=wallet,
                payment_method=tx.payment_method,
                topup_transaction=tx,
                amount=amount,
                tx_id=dep_txid or None,
                status="completed",
            )

            BEP20ActiveAmount.objects.filter(amount=amount).delete()
            print(f"[BEP20] ✅ Payment confirmed and wallet credited.")

            return Response({
                "success": True,
                "amount": f"{amount:.2f}",
                "balance": f"{wallet.balance:.2f}",
                "telegram_id": tx.user.telegram_id,
            })

        print(f"[BEP20] ❌ No matching deposit found after checking {len(deposit_list)} records.")
        return Response(
            {"detail": "❌ No matching BEP20 deposit found. Please wait a moment and try again."},
            status=status.HTTP_404_NOT_FOUND,
        )

