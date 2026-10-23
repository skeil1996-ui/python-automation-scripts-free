import importlib.util
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inv = load("invoice-generator/invoice_lite.py")
mail = load("email-attachment-saver/attachment_saver_lite.py")
shop = load("shopify-stock-check/stock_check_lite.py")
yt = load("youtube-comment-export/yt_comments_lite.py")


class InvoiceLite(unittest.TestCase):
    def test_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "i.csv"
            p.write_text("invoice_number,client_name,description,quantity,unit_price\n"
                         "A1,Acme,Work,2,100\nA1,Acme,Hosting,1,9.99\nA2,Bob,Logo,1,350\n")
            self.assertEqual(inv.main([str(p), "--tax", "19", "--currency", "EUR", "-o", d + "/out"]), 0)
            pdfs = sorted(x.name for x in Path(d, "out").glob("*.pdf"))
            self.assertEqual(pdfs, ["A1_Acme.pdf", "A2_Bob.pdf"])
            self.assertTrue(Path(d, "out", "A1_Acme.pdf").read_bytes().startswith(b"%PDF"))

    def test_semicolon_and_comma(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "i.csv"
            p.write_text("invoice_number;client_name;description;quantity;unit_price\nR1;Müller;Beratung;2,5;1.200,00\n")
            invs = inv.load(p)
            self.assertEqual(str(invs["R1"]["items"][0][3]), "3000.00")

    def test_missing_column(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "i.csv"
            p.write_text("invoice_number,client_name\n1,a\n")
            with self.assertRaises(SystemExit):
                inv.load(p)


class FakeIMAP:
    def __init__(self, msgs):
        self.msgs = msgs

    def login(self, u, p):
        self.pw = p

    def select(self, f, readonly=False):
        self.ro = readonly

    def uid(self, cmd, *a):
        if cmd == "SEARCH":
            return "OK", [b" ".join(str(i).encode() for i in self.msgs)]
        return "OK", [(b"x", self.msgs[int(a[0])])]

    def logout(self):
        pass


class MailLite(unittest.TestCase):
    def test_saves_only_pdfs(self):
        m = EmailMessage()
        m["From"], m["Subject"] = "billing@shop.com", "Invoice"
        m.set_content("hi")
        m.add_attachment(b"%PDF-1", maintype="application", subtype="pdf", filename="inv.pdf")
        m.add_attachment(b"img", maintype="image", subtype="png", filename="logo.png")
        imap = FakeIMAP({1: m.as_bytes(), 2: m.as_bytes()})
        with tempfile.TemporaryDirectory() as d:
            n = mail.run("h", "u", "ab cd", "shop.com", Path(d), imap=imap)
            self.assertEqual(n, 2)
            self.assertEqual(sorted(x.name for x in Path(d).iterdir()), ["inv (1).pdf", "inv.pdf"])
            self.assertTrue(imap.ro)
            self.assertEqual(imap.pw, "abcd")


class ShopLite(unittest.TestCase):
    def test_low_stock_and_paging(self):
        def node(t, q, sku="", status="ACTIVE", tracked=True, vt="Default Title"):
            return {"title": vt, "sku": sku, "inventoryQuantity": q, "inventoryItem": {"tracked": tracked},
                    "product": {"title": t, "status": status}}
        pages = [[node("Mug", 2, "M1"), node("Tee", 50)], [node("Cap", 0, vt="Red"), node("Draft", 0, status="DRAFT"),
                                                           node("Ebook", 0, tracked=False)]]
        calls = []

        def post(body):
            i = 0 if body["variables"]["c"] is None else 1
            calls.append(i)
            return {"data": {"productVariants": {"edges": [{"node": n} for n in pages[i]],
                                                 "pageInfo": {"hasNextPage": i == 0, "endCursor": "x"}}}}
        rows = shop.low_stock(shop.fetch("s.myshopify.com", "t", "2026-07", post=post), 5)
        self.assertEqual(rows, [(0, "Cap - Red"), (2, "Mug (SKU M1)")])
        self.assertEqual(calls, [0, 1])


class YTLite(unittest.TestCase):
    def test_ids_and_paging(self):
        self.assertEqual(yt.video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

        def get(p):
            item = lambda n: {"snippet": {"totalReplyCount": 1, "topLevelComment": {"snippet": {
                "authorDisplayName": n, "textDisplay": "hi?", "likeCount": 3, "publishedAt": "2026"}}}}
            return {"items": [item("a")], "nextPageToken": "n"} if "pageToken" not in p else {"items": [item("b")]}
        rows = yt.comments("dQw4w9WgXcQ", "k", get=get)
        self.assertEqual([r["author"] for r in rows], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
