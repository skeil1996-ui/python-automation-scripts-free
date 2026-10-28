# Free Python Automation Scripts

Five small, free scripts that save time on boring computer work. Pure Python 3.8+, no accounts, no cloud, mostly no installs. Windows, macOS and Linux.

| Script | What it does | Free version | Full version |
|---|---|---|---|
| [File Organizer](file-organizer/) | Sorts a messy folder into Images / Documents / Videos / … | Sort by type, dry-run, undo | + bulk rename, sort by date, filters, full history – [€9](https://skeilster.gumroad.com/l/file-organizer) |
| [Invoice Generator](invoice-generator/) | CSV of line items → PDF invoices | Simple layout, one tax rate | + your logo & colours, several tax rates, German/English, no footer note – [€19](https://skeilster.gumroad.com/l/invoice-generator) |
| [Email Attachment Saver](email-attachment-saver/) | Saves PDF attachments from your inbox | One sender, PDFs, run once | + any file types, all filters, dated folders, watch mode, no duplicates – [€12](https://skeilster.gumroad.com/l/gmail-attachment-saver) |
| [Shopify Stock Check](shopify-stock-check/) | Lists products that are running low | One-time list in the terminal | + automatic alerts to Discord / Slack / Telegram / email, per-SKU thresholds – [€29](https://skeilster.gumroad.com/l/shopify-low-stock-bot) |
| [YouTube Comment Export](youtube-comment-export/) | Exports a video's comments to Excel | Top-level comments, one video | + all replies, whole channels, insights report with your audience's questions – [€24](https://skeilster.gumroad.com/l/youtube-comment-exporter) |

## More tools

- [Dupe Dir Duplicate Text Finder (free + full)](https://skeilster.gumroad.com/l/jjulwj) – Find near-duplicate text entries across folders of TXT, MD, and CSV files before they clutter your knowledge base.
- [Git Branch Cleanup Tool (free + full)](https://skeilster.gumroad.com/l/uvpwln) – Safely find and remove stale, already-merged Git branches in one command.
- [Duplicate Photo Finder Pro](https://skeilster.gumroad.com/l/nejwxp) – finds exact and near-duplicate photos, dry-run first, quarantine instead of delete – €12

All paid tools: https://skeilster.gumroad.com

## Quick start

Download this repo (green **Code** button → **Download ZIP**), unzip, open a terminal in the folder.

```bash
# File Organizer – preview, sort, undo
python file-organizer/organizer.py ~/Downloads --dry-run
python file-organizer/organizer.py ~/Downloads
python file-organizer/organizer.py --undo ~/Downloads

# Invoice Generator (needs: pip install reportlab)
python invoice-generator/invoice_lite.py invoices.csv --company "My Shop" --tax 19 --currency "€"
#   CSV columns: invoice_number, client_name, description, quantity, unit_price

# Email Attachment Saver – Gmail needs an App Password: https://myaccount.google.com/apppasswords
python email-attachment-saver/attachment_saver_lite.py --email you@gmail.com --from billing@shop.com

# Shopify Stock Check – Admin API token with read_products + read_inventory
python shopify-stock-check/stock_check_lite.py --shop your-store.myshopify.com --token shpat_xxx --threshold 5

# YouTube Comment Export – free key: console.cloud.google.com → enable "YouTube Data API v3" → API key
python youtube-comment-export/yt_comments_lite.py https://youtu.be/VIDEO_ID --api-key YOUR_KEY
```

Every script shows its options with `--help`.

## Tests

```bash
python -m unittest discover -s tests
python -m unittest discover -s file-organizer/tests
```

## License

MIT – free to use, modify and share. The paid full versions have their own license.
