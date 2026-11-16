"""
E-Commerce Automated Test Suite & QA Checklist.
==============================================
Validates all critical business rules for the shopping cart and checkout.
Used by the Bug Fixer Agent to detect regressions and certify production readiness.
"""

import unittest
from ecommerce.cart import ECommerceCart, Product


class TestECommerceCart(unittest.TestCase):
    """
    Test suite enforcing the E-Commerce Store Checklist.
    """

    def setUp(self):
        """Set up test catalog."""
        self.cart = ECommerceCart()
        self.laptop = Product(id="prod_01", name="Developer Laptop", price=999.99, stock=5)
        self.mouse = Product(id="prod_02", name="Wireless Mouse", price=25.50, stock=10)
        self.tshirt = Product(id="prod_03", name="Wolf Dev T-Shirt", price=19.99, stock=3)

    def test_checklist_1_subtotal_calculation(self):
        """[CHECKLIST-1] Subtotal should accurately sum item price * quantity."""
        self.cart.add_item(self.mouse, quantity=2)  # 25.50 * 2 = 51.00
        self.cart.add_item(self.tshirt, quantity=1) # 19.99 * 1 = 19.99
        self.assertEqual(self.cart.calculate_subtotal(), 70.99)

    def test_checklist_2_discount_coupon_percentage(self):
        """[CHECKLIST-2] Valid coupon (e.g. SAVE20) should deduct 20% from subtotal."""
        self.cart.add_item(self.mouse, quantity=2)  # Subtotal = 51.00
        res = self.cart.apply_coupon("SAVE20")
        self.assertTrue(res["success"])
        # 51.00 * 0.20 = 10.20 discount
        self.assertEqual(self.cart.calculate_discount(), 10.20)

    def test_checklist_3_tax_calculated_on_discounted_amount(self):
        """[CHECKLIST-3] Tax (8%) must apply to discounted net subtotal, not full price."""
        self.cart.add_item(self.mouse, quantity=2)  # 51.00
        self.cart.apply_coupon("SAVE20")            # Discount = 10.20 -> Taxable = 40.80
        # Tax = 40.80 * 0.08 = 3.264 -> 3.26
        self.assertEqual(self.cart.calculate_tax(), 3.26)

    def test_checklist_4_free_shipping_threshold(self):
        """[CHECKLIST-4] Free shipping for orders >= $50; flat $5.99 below $50."""
        # Case A: Net total under $50 -> $5.99 shipping
        self.cart.add_item(self.tshirt, quantity=1) # 19.99
        self.assertEqual(self.cart.calculate_shipping(), 5.99)

        # Case B: Net total over $50 -> Free shipping ($0.00)
        self.cart.add_item(self.mouse, quantity=2)  # +51.00 = 70.99
        self.assertEqual(self.cart.calculate_shipping(), 0.0)

    def test_checklist_5_inventory_oversell_prevention(self):
        """[CHECKLIST-5] Adding more items than in stock must raise ValueError."""
        # T-shirt stock is only 3
        with self.assertRaises(ValueError):
            self.cart.add_item(self.tshirt, quantity=5)

    def test_checklist_6_currency_rounding_and_grand_total(self):
        """[CHECKLIST-6] Grand total = (Subtotal - Discount) + Tax + Shipping rounded to 2 decimals."""
        self.cart.add_item(self.mouse, quantity=2)   # Subtotal = 51.00
        self.cart.apply_coupon("SAVE10")             # 10% discount = 5.10 -> Net = 45.90
        # Net 45.90 is < $50 -> shipping = 5.99
        # Tax = 45.90 * 0.08 = 3.672 -> 3.67
        # Total = 45.90 + 3.67 + 5.99 = 55.56
        self.assertEqual(self.cart.calculate_total(), 55.56)


if __name__ == "__main__":
    unittest.main()
