# GBF-Bookmaker-Scraper

Simple script that scrapes the bookmaker scores every 20 minutes and updates a spreadsheet as well as outputs to a discord webhook accordingly. Loosely based off of kyoukaya's [gbf-scraper](https://github.com/kyoukaya/gbf-scraper)

## Installation

* [Python 3.6](https://www.python.org/downloads/)
* The following packages:
  * selenium
  * seleniumrequests
  * oauth2client
  * BeautifulSoup
  * gspread
  * plotly
  * discord [development version]
* Chrome/chromium
* [Chrome webdriver](https://sites.google.com/a/chromium.org/chromedriver/downloads) (Must be in the same directory)

* Setting up oauth2 to use google docs spreadsheets:
  1. Go to the [Google APIs Console](https://console.developers.google.com/).
  2. Create a new project.
  3. Click *Enable API*. Search for and enable the Google Drive API and Google Sheets API.
  4. *Create credentials* for a *Web Server* to access *Application Data*.
  5. Name the service account and grant it a *Project Role* of *Editor*.
  6. Download the JSON file.
  7. Copy the JSON file to the same directory and rename it to `client_secret.json`
  8. Create a google docs spreadsheet called **GW Points** under any account.
  9. Open `client_secret.json` and find `client_email` inside and copy this e-mail address.
  10. On the google docs spreadsheet, share the spreadsheet to the e-mail that was copied and ensure that it has permission to edit.

![](https://i.imgur.com/fzwqc2u.gif)
  
 ## Usage
 The GW identifier must be 3 digits. e.g. `035` for the 35th GW.
`usage: bookmaker-scraper.py [profile] [GW] [options]`

`example: python bookmaker-scraper.py profile1 035 -l`

|flag|arguments|description|
|---------|---------|-----------|
|--login, -l|None|Pauses the script upon starting up to allow logging in|