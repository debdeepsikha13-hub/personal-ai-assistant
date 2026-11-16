"""
E-Commerce Cart & Order Checkout System.
=========================================
Handles products, inventory, cart management, discount coupons,
tax calculation, and order checkout.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int
    category: str = "General"


@dataclass
class CartItem:
    product: Product
    quantity: int


class ECommerceCart:
    """
    Main E-Commerce Cart & Checkout Engine.
    """
    # Active store discount coupons
    VALID_COUPONS = {
        "SAVE10": 0.10,  # 10% off
        "SAVE20": 0.20,  # 20% off
        "WOLF50": 0.50   # 50% off VIP discount
    }

    TAX_RATE = 0.08  # 8% State Sales Tax
    FREE_SHIPPING_THRESHOLD = 50.00  # Orders over $50 get free shipping
    STANDARD_SHIPPING_FEE = 5.99

    def __init__(self):
        self.items: Dict[str, CartItem] = {}
        self.applied_coupon: Optional[str] = None

    def add_item(self, product: Product, quantity: int = 1) -> bool:
        """Add a product to cart with strict inventory check."""
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        
        current_in_cart = self.items[product.id].quantity if product.id in self.items else 0
        total_requested = current_in_cart + quantity

        # Inventory check: cannot exceed available stock
        if total_requested > product.stock:
            raise ValueError(
                f"Cannot add {quantity} units. Only {product.stock} available in stock (already in cart: {current_in_cart})."
            )

        if product.id in self.items:
            self.items[product.id].quantity += quantity
        else:
            self.items[product.id] = CartItem(product=product, quantity=quantity)
        return True

    def remove_item(self, product_id: str) -> bool:
        """Remove a product completely from cart."""
        if product_id in self.items:
            del self.items[product_id]
            return True
        return False

    def apply_coupon(self, coupon_code: str) -> Dict[str, any]:
        """Apply a promotional discount code."""
        code = coupon_code.strip().upper()
        if code not in self.VALID_COUPONS:
            raise ValueError(f"Invalid coupon code: '{coupon_code}'. Valid codes: {list(self.VALID_COUPONS.keys())}")
        
        self.applied_coupon = code
        discount_pct = self.VALID_COUPONS[code] * 100
        return {
            "success": True,
            "coupon": code,
            "discount_percentage": discount_pct,
            "message": f"Coupon {code} applied successfully! ({discount_pct:.0f}% OFF)"
        }

    def calculate_subtotal(self) -> float:
        """Calculate raw subtotal of items in cart before discounts."""
        total = sum(item.product.price * item.quantity for item in self.items.values())
        return round(total, 2)

    def calculate_discount(self) -> float:
        """Calculate discount amount based on applied coupon."""
        if not self.applied_coupon:
            return 0.0
        
        subtotal = self.calculate_subtotal()
        rate = self.VALID_COUPONS.get(self.applied_coupon, 0.0)
        return round(subtotal * rate, 2)

    def calculate_tax(self) -> float:
        """
        Calculate sales tax.
        Rule: Tax must be calculated on the discounted subtotal, not full price!
        """
        subtotal = self.calculate_subtotal()
        discount = self.calculate_discount()
        taxable_amount = max(0.0, subtotal - discount)
        return round(taxable_amount * self.TAX_RATE, 2)

    def calculate_shipping(self) -> float:
        """Calculate shipping fee. Free if discounted subtotal >= $50."""
        subtotal = self.calculate_subtotal()
        discount = self.calculate_discount()
        net_amount = subtotal - discount

        if net_amount <= 0:
            return 0.0
        if net_amount >= self.FREE_SHIPPING_THRESHOLD:
            return 0.0  # Free shipping
        return self.STANDARD_SHIPPING_FEE

    def calculate_total(self) -> float:
        """
        Calculate final order grand total:
        Total = (Subtotal - Discount) + Tax + Shipping
        """
        subtotal = self.calculate_subtotal()
        discount = self.calculate_discount()
        tax = self.calculate_tax()
        shipping = self.calculate_shipping()

        grand_total = (subtotal - discount) + tax + shipping
        return round(grand_total, 2)

    def get_order_summary(self) -> Dict[str, any]:
        """Generate structured breakdown of the cart for checkout."""
        subtotal = self.calculate_subtotal()
        discount = self.calculate_discount()
        tax = self.calculate_tax()
        shipping = self.calculate_shipping()
        total = self.calculate_total()

        return {
            "items_count": sum(item.quantity for item in self.items.values()),
            "subtotal": subtotal,
            "coupon": self.applied_coupon or "None",
            "discount": discount,
            "tax": tax,
            "shipping": shipping,
            "grand_total": total,
            "is_free_shipping": (shipping == 0.0 and (subtotal - discount) >= self.FREE_SHIPPING_THRESHOLD)
        }
