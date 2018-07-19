# import libraries
from time import time as time_now
from time import sleep, strftime
from selenium import webdriver
from os import makedirs, path
from bs4 import BeautifulSoup
import argparse
from sys import argv
import threading
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pytz import timezone    
from random import randint
import plotly
import plotly.plotly as py
import plotly.offline as offline
import plotly.graph_objs as go
import requests
import discord
from discord import Webhook, RequestsWebhookAdapter, File

from config import config

CHECK_FREQUENCY = 1200.0 # in seconds

GW_NUM = '036'
GW_URL = 'http://game.granbluefantasy.jp/#event/teamraid{}'.format(GW_NUM)

#https://discordapp.com/api/webhooks/<DISCORD_WEBHOOK_ID>/<DISCORD_WEBHOOK_TOKEN>

DISCORD_WEBHOOK_ID = [
  'EXAMPLE_WEBHOOK_ID1234567890'
]
DISCORD_WEBHOOK_TOKEN = [
  'EXAMPLE_WEBHOOK_TOKENabcdefgh123456'
]

CHROME_ARGUMENTS = '--disable-infobars'

LOG_FILE = '[{}]granblue-scraper.log'.format(strftime('%m-%d_%H%M'))

def log(message):
  '''Prints to console and outputs to log file'''

  try:
    with open('.\\logs\\' + LOG_FILE, 'a',
        encoding='utf-8', newline='') as fout:
      message = '[%s] %s' % (strftime('%a %H:%M:%S'), message)
      print(message)
      print(message, file=fout)
  except FileNotFoundError:
    makedirs('.\\logs')
    log('Created log folder')
    log(message)

def main():
  global GBF
  timestart = time_now()
  profile = path.abspath(".\\" + CFG.profile)

  parser = argparse.ArgumentParser(prog='matchup-scraper.py',
    description='A simple script for scraping various parts of Granblue Fantasy',
    usage='bookmaker-scraper.py [profile] [gw] [options]\nexample: python bookmaker-scraper.py profile2 035 5 -l',
    formatter_class=argparse.MetavarTypeHelpFormatter)

  parser.add_argument('profile', nargs='?',
    help='overwrites the default profile path', type=str)
  parser.add_argument('gw', nargs=1,
    help='scrapes matchup scores based on gw', type=str)
  parser.add_argument('--login', '-l',
    help='pauses the script upon starting up to allow logging in', action='store_true')
  args = parser.parse_args()

  if len(argv) == 1:
    parser.print_help()
    quit()

  if args.profile is not None:
    log('Changing profile path to {}'.format(args.profile))
    profile = path.abspath('.\\' + args.profile)

  if args.gw is not None and len(args.gw) == 1:
    log('Parsing scores for GW {}'.format(args.gw[0]))
    GW_NUM = args.gw[0]
    GW_URL = 'http://game.granbluefantasy.jp/#event/teamraid{}'.format(GW_NUM)
    BOOKMAKER_URL = GW_URL + '/bookmaker'
  else:
    parser.print_help()
    quit()

  options = webdriver.ChromeOptions()
  log('Using profile at: {}'.format(profile))
  options.add_argument('user-data-dir=%s' % profile)
  for cargs in CHROME_ARGUMENTS.split():
    options.add_argument(cargs)
  GBF = webdriver.Chrome(chrome_options=options)
  GBF.get('http://game.granbluefantasy.jp/#mypage')

  if args.login:
    log('Pausing to login')
    input('Press enter to continue...')

  jp_tz = timezone('Asia/Tokyo')

  while True:
    GBF.get(BOOKMAKER_URL);
    GBF.refresh();
    sleep(5)
    data = BeautifulSoup(GBF.page_source, 'html.parser')

    north = 0
    west  = 0
    east  = 0
    south = 0
    
    log('Finding match day')
    day = data.find('div', attrs={'class': 'prt-battle-num'})
    if day['class'][1] is None:
      log('No match day found')
      sleep(CHECK_FREQUENCY - ((time_now() - timestart) % CHECK_FREQUENCY))
      continue
    day = int(day['class'][1].replace('battle-num', ''))
    if day is None:
      log('No match day found')
      sleep(CHECK_FREQUENCY - ((time_now() - timestart) % CHECK_FREQUENCY))
      continue
    log('Found match day: {}'.format(day))
    
    log('Opening Google spreadsheet')
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open('GBF Bookmaker Tallies')
    try:
      worksheet = spreadsheet.worksheet('GW {} - Day {}'.format(GW_NUM, day))
    except Exception:
      GBF.close()
      raise
    log('Google spreadsheet opened')

    log('Finding bookmaker scores')
    scores = data.find('div', attrs={'class': 'prt-area-list'})
    if scores is not None:
      log('Found bookmaker scores')
      north = int(scores.find('div', attrs={'class': 'lis-area area1'}).find('div', attrs={'class': 'point'}).text.strip().replace(',', ''))
      west  = int(scores.find('div', attrs={'class': 'lis-area area2'}).find('div', attrs={'class': 'point'}).text.strip().replace(',', ''))
      east  = int(scores.find('div', attrs={'class': 'lis-area area3'}).find('div', attrs={'class': 'point'}).text.strip().replace(',', ''))
      south = int(scores.find('div', attrs={'class': 'lis-area area4'}).find('div', attrs={'class': 'point'}).text.strip().replace(',', ''))
      log('north: {}, west: {}, east: {}, south: {}'.format(north, west, east, south))
      log('Finding spreadsheet row')
      currTime = datetime.now(jp_tz)
      if currTime.hour == 0:
        row = 61
      elif currTime.hour < 7:
        row = -1
      else:
        row = (currTime.hour - 7) * 3 + currTime.minute // 20 + 10
      log('row: {}'.format(row))

      if row >= 10 and row <= 61:
        log('Updating spreadsheet')
        worksheet.update_cell(row, 3, north)
        worksheet.update_cell(row, 4, west)
        worksheet.update_cell(row, 5, east)
        worksheet.update_cell(row, 6, south)

        log('Sign into plotly')
        plotly.tools.set_credentials_file(username='YOUR_PLOTLY_USERNAME', api_key='YOUR_PLOTLY_API_KEY')
        py.sign_in('YOUR_PLOTLY_USERNAME', 'YOUR_PLOTLY_API_KEY')

        cell_list = worksheet.range('R12:V63')
        scoreIntervals = []
        nScoreDiffs = []
        wScoreDiffs = []
        eScoreDiffs = []
        sScoreDiffs = []
        i = 0
        for cell in cell_list:
          col = i % 5
          if col == 0:
            scoreIntervals.append(cell.value)
          elif col == 1:
            nScoreDiffs.append(cell.value)
          elif col == 2:
            wScoreDiffs.append(cell.value)
          elif col == 3:
            eScoreDiffs.append(cell.value)
          elif col == 4:
            sScoreDiffs.append(cell.value)
          i+=1
        log('Plot data retrieved')

        nScore = worksheet.acell('C{}'.format(row)).value
        wScore = worksheet.acell('D{}'.format(row)).value
        eScore = worksheet.acell('E{}'.format(row)).value
        sScore = worksheet.acell('F{}'.format(row)).value
        currRank = worksheet.acell('G{}'.format(row)).value

        nScorePrediction = worksheet.acell('J38').value
        wScorePrediction = worksheet.acell('K38').value
        eScorePrediction = worksheet.acell('L38').value
        sScorePrediction = worksheet.acell('M38').value
        predictedRank = worksheet.acell('N38').value
        log('Spreadsheet updated')
        
        trace0 = go.Scatter(
          x = scoreIntervals,
          y = nScoreDiffs,
          mode = 'lines+markers',
          name = 'N'
        )
        trace1 = go.Scatter(
          x = scoreIntervals,
          y = wScoreDiffs,
          mode = 'lines+markers',
          name = 'W'
        )
        trace2 = go.Scatter(
          x = scoreIntervals,
          y = eScoreDiffs,
          mode = 'lines+markers',
          name = 'E'
        )
        trace3 = go.Scatter(
          x = scoreIntervals,
          y = sScoreDiffs,
          mode = 'lines+markers',
          name = 'S'
        )
        log('Plot trendlines generated')
        
        data = [trace0, trace1, trace2, trace3]
        layout = go.Layout(title='Difference Over North', width=1000, height=640)
        fig = go.Figure(data=data, layout=layout)

        py.image.save_as(fig, filename='plot.png')

        log('Plot object created')
        from IPython.display import Image
        Image('plot.png')
        log('Plot image generated')
        log('Send to discord webhooks')
        embed = discord.Embed(title='GW {} - Day {}'.format(GW_NUM, day), description='[Click here](YOUR_SPREADSHEET_URL) to view the full spreadsheet.\nPredicted winners are based on their **CURRENT** average point per hour. It does not account for previous trends.')
        embed.add_field(name='Current', value='```Rank:  {}\nNorth: {}\nWest:  {}\nEast:  {}\nSouth: {}```'.format(currRank, nScore, wScore, eScore, sScore), inline=True)
        embed.add_field(name='Predicted', value='```Rank:  {}\nNorth: {}\nWest:  {}\nEast:  {}\nSouth: {}```'.format(predictedRank, nScorePrediction, wScorePrediction, eScorePrediction, sScorePrediction), inline=True)
        embed.set_footer(text=datetime.now(jp_tz).strftime('%a, %b %d, %Y at %I:%M:%S %p JST'))

        i = 0
        for idx in DISCORD_WEBHOOK_ID:
          webhook = Webhook.partial(DISCORD_WEBHOOK_ID[i], DISCORD_WEBHOOK_TOKEN[i],\
            adapter=RequestsWebhookAdapter())
          webhook.send(embed=embed, file=discord.File("plot.png"))
          i+=1
    log('Update completed')
    sleep(CHECK_FREQUENCY - ((time_now() - timestart) % CHECK_FREQUENCY))

if __name__ == '__main__':
  CFG = config()

  try:
    main()
  except Exception:
    GBF.close()
    raise
