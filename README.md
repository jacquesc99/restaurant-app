# Allergen & Dietary Filter App

A web application that allows restaurants to upload their menu as a CSV file and generate a QR code that guests can scan to filter dishes based on their dietary restrictions and allergens.

---

## Legal Disclaimer

**IMPORTANT — PLEASE READ BEFORE USE**

This application is provided for **reference purposes only**. It is not a medical tool and must not be used as a substitute for professional medical or dietary advice.

- Guests with severe allergies or medical dietary requirements should always speak directly with restaurant staff before ordering.
- The accuracy of allergen and dietary information displayed is entirely dependent on the data uploaded by the restaurant. **The developer of this application accepts no responsibility for incorrect, incomplete, or outdated menu data.**
- It is the sole responsibility of the restaurant operator uploading data to ensure that all information is accurate, current, and compliant with applicable food safety regulations.
- The developer of this application is not liable for any health-related issues, allergic reactions, or adverse events arising from the use of this application or reliance on the information it displays.
- By using this application, restaurants agree to take full responsibility for the accuracy of the data they upload and the information presented to their guests.

**Use with caution. Always verify allergen information directly with your server or kitchen staff.**

---

## For Restaurants — Step by Step Setup Guide

### Step 1 — Sign Up

1. Go to the app's homepage and click **Sign Up**
2. Enter your restaurant name, email address, and a password
3. You will be automatically logged in and taken to your dashboard

Your restaurant will be assigned a unique URL in the format:
```
https://yourapp.com/menu/your-restaurant-name
```

---

### Step 2 — Prepare Your CSV File

Your menu must be formatted as a CSV file. Open Excel or Google Sheets and create columns in this order:

| dish | category | pork | gluten | dairy | egg | ... | alt_gluten | alt_dairy | alt_pork |
|------|----------|------|--------|-------|-----|-----|------------|-----------|----------|
| Margherita Pizza | Pizza | FALSE | TRUE | TRUE | FALSE | ... | Gluten Free Crust | Vegan Mozzarella | |
| Caesar Salad | Salad | FALSE | TRUE | TRUE | TRUE | ... | No Croutons | Dressing on Side | |

**Rules for your CSV:**

- The first column must be named `dish`
- The second column should be named `category` (optional but recommended)
- All allergen columns must be `TRUE` or `FALSE`
- For alternatives, create a column named `alt_` followed by the allergen name (e.g. `alt_gluten`, `alt_dairy`, `alt_pork`)
- Leave alternative cells blank if there is no modification available for that allergen
- Save the file as `.csv` format

**Supported allergen column names:**

| Column Name | Description |
|-------------|-------------|
| `pork` | Contains pork |
| `beef` | Contains beef |
| `chicken` | Contains chicken/poultry |
| `egg` | Contains egg |
| `dairy` | Contains dairy |
| `fish` | Contains fish |
| `shellfish` | Contains shellfish |
| `gluten` | Contains gluten |
| `peanuts` | Contains peanuts |
| `tree nuts` | Contains tree nuts |
| `soy` | Contains soy |
| `sesame` | Contains sesame |
| `capsaicin` | Contains capsaicin (spice) |
| `piperine` | Contains piperine (black pepper) |
| `vegetarian` | Suitable for vegetarians |
| `vegan` | Suitable for vegans |
| `pregnancy safe` | Safe for pregnant guests |

---

### Step 3 — Upload Your CSV

1. Log in to your dashboard
2. Under **Upload Menu CSV**, click **Choose File**
3. Select your `.csv` file and click **Upload**
4. You will see a confirmation message: *Menu uploaded successfully!*

To update your menu at any time, simply upload a new CSV file — it will replace the previous one.

---

### Step 4 — Get Your QR Code

Your QR code is automatically generated on your dashboard. It points to your unique menu URL.

1. Right-click the QR code image and save it
2. Print it and display it on your tables, menus, or entrance
3. Guests scan the QR code with their phone camera and are taken directly to your allergen filter page — no app download required

---

### Step 5 — How Guests Use It

1. Guest scans the QR code
2. They see a list of dietary filters (gluten, dairy, vegan, etc.)
3. They select their restrictions and tap **Find Safe Dishes**
4. Results show:
   - ✅ **Green** — safe to eat as-is
   - ⚠️ **Orange** — can be modified, with specific modifications listed
   - Hidden — not suitable and no modification available

---

## Updating Your Menu

Log in to your dashboard at any time and upload a new CSV file. Changes are reflected immediately on your live menu page.

---

## Support

For technical issues contact the app administrator. Restaurant operators are responsible for ensuring their menu data is accurate and up to date at all times.
