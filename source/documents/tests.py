from django.test import TestCase
from django.urls import reverse

from .registry import registry


class RegistryTests(TestCase):
    def test_accounting_documents_are_registered(self):
        self.assertIsNotNone(registry.get("accounting", "invoice"))
        self.assertIsNotNone(registry.get("accounting", "quote"))

    def test_unknown_document_returns_404(self):
        url = reverse("documents:panel", args=["accounting", "unknown"])
        self.assertEqual(self.client.get(url).status_code, 404)


class ViewTests(TestCase):
    def test_panel_returns_form_and_frame(self):
        url = reverse("documents:panel", args=["accounting", "invoice"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-doc-form")
        self.assertContains(response, "data-doc-preview")

    def test_panel_has_customize_section_and_line_editor(self):
        url = reverse("documents:panel", args=["accounting", "invoice"])
        response = self.client.get(url)
        self.assertContains(response, "doc-customize")
        self.assertContains(response, "data-doc-lines")
        self.assertContains(response, "data-doc-action")

    @staticmethod
    def _invoice_params(**overrides):
        """A full parameter set, as the panel form sends it."""
        params = {
            "paper_size": "A4", "accent_color": "#F0BE72",
            "company_name": "Pothos ERM Suite", "company_details": "",
            "customer": "aster", "currency": "R", "tax_rate": "15",
            "notes": "", "number": "INV-1", "issue_date": "2026-08-30",
            "due_date": "2026-09-29", "payment_details": "",
            "line_items": "[]",
        }
        params.update(overrides)
        return params

    def test_preview_accepts_custom_line_items(self):
        url = reverse("documents:preview", args=["accounting", "invoice"])
        items = ('[{"description": "One-off fee", "unit": "",'
                 ' "quantity": "2", "unit_price": "10.50"}]')
        response = self.client.get(url, self._invoice_params(line_items=items))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_broken_line_items_return_400(self):
        url = reverse("documents:preview", args=["accounting", "invoice"])
        response = self.client.get(url, self._invoice_params(line_items="not json"))
        self.assertEqual(response.status_code, 400)

    def test_preview_returns_inline_pdf(self):
        url = reverse("documents:preview", args=["accounting", "invoice"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_download_returns_attachment(self):
        url = reverse("documents:download", args=["accounting", "quote"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_bad_options_return_400(self):
        url = reverse("documents:preview", args=["accounting", "invoice"])
        response = self.client.get(url, {"tax_rate": "not-a-number"})
        self.assertEqual(response.status_code, 400)
