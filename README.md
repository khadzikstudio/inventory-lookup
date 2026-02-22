# Inventory Lookup

A searchable inventory database with AI-powered visual search. Import your items from an Excel spreadsheet with product images, then search using natural language like "blue furniture" — it matches both text fields and what the images actually look like.

## Quick Start

### 1. Install dependencies
```
setup.bat
```

### 2. Configure
Edit `config.yaml`:
- `spreadsheet` — path to your `.xlsx` file
- `image_folder` — path to the folder containing product images
- `columns` — map the column names to match your spreadsheet headers

### 3. Import data
```
python import_data.py
```
This reads the spreadsheet, links images, generates thumbnails, and computes AI embeddings. First run downloads the CLIP model (~400MB).

### 4. Start the server
```
start.bat
```
Then open http://localhost:5000 in your browser.

## How Search Works

- **Text search** — matches item name, category, and extra fields using SQLite full-text search
- **Visual search** — uses OpenAI's CLIP model to understand what images look like and match them to your search query
- **Hybrid ranking** — results from both methods are combined so items matching both text and visuals rank highest

## Re-importing

To update the database after changing the spreadsheet:
```
python import_data.py --clear
```
