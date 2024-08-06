import feedparser
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from transformers import pipeline
import os
import pandas as pd
from googletrans import Translator, LANGUAGES

# Hugging Face model settings
model_name = "distilbert-base-uncased-finetuned-sst-2-english"
nlp = pipeline("sentiment-analysis", model=model_name)

# Initialize translator
translator = Translator()

# Add RSS feed URLs
rss_urls = {
    "Armenia": [
        "https://en.1in.am/feed",
        "https://a1plus.am/en/feed",
        "https://life.mediamall.am/?rss"
    ],
    "Georgia": [
        "https://civil.ge/feed"
    ],
    "Greece": [
        "https://www.in.gr/feed/?rid=2&pid=250&la=1&si=1",
        "https://feeds.feedburner.com/newsbombgr",
        "https://www.newsit.gr/feed/",
        "https://www.protothema.gr/rss"
    ],
    "Iran": [
        "https://ir.voanews.com/api/zkup_empmy"
    ],
    "Iraq": [
        "https://www.ahewar.org/rss/default.asp?lt=7"
    ],
    "Syria": [
        "https://www.sana.sy/tr/?feed=rss2"
    ],
    "Bulgaria": [
        "https://dnes.dir.bg/support/cat_rss.php",
        "https://www.dnes.bg/rss.php?today",
        "https://www.24chasa.bg/rss"
    ]
}

# Set desktop path
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

# Current date and 00:00 of the previous day
now = datetime.now()
start_of_yesterday = datetime(now.year, now.month, now.day) - timedelta(days=1)

def translate_to_english(text):
    try:
        translated = translator.translate(text, dest='en')
        return translated.text
    except Exception as e:
        print(f"Translation failed for text: {text}. Error: {e}")
        return text

def analyze_with_local_model(texts):
    results = nlp(texts)
    threat_percentage = 0.0
    positive_titles = []
    negative_titles = []
    for result, text in zip(results, texts):
        if result['label'] == 'NEGATIVE':  # Negative sentiment
            threat_percentage += 0.01
            negative_titles.append((text, 0.01))
        elif result['label'] == 'POSITIVE':  # Positive sentiment
            positive_titles.append((text, 0.01))
    return threat_percentage, negative_titles, positive_titles

# Calculate current threat
threats = {}
all_negative_titles = []
all_positive_titles = []

for country, urls in rss_urls.items():
    print(f"\n{'='*20}\nCountry: {country}\n{'='*20}")
    daily_entries = []
    for url in urls:
        feed = feedparser.parse(url)
        entries = feed.entries
        
        # Filter news with date information
        for entry in entries:
            published_date_str = entry.get('published', None)
            if published_date_str:
                try:
                    published_date = date_parser.parse(published_date_str)
                    published_date = published_date.replace(tzinfo=None)
                    if published_date >= start_of_yesterday:
                        daily_entries.append(entry)
                except ValueError:
                    continue

        # If no news with date information found, take the last 20 entries
        if not daily_entries:
            daily_entries = entries[:20]
        
    # Print daily data
    os.makedirs(desktop_path, exist_ok=True)
    file_path = os.path.join(desktop_path, f"{country}_news.txt")
    with open(file_path, "w", encoding="utf-8") as file:  # Specify encoding here
        if daily_entries:
            titles = [entry.title for entry in daily_entries]
            
            # Translate titles to English if necessary
            translated_titles = [translate_to_english(title) if not title.isascii() else title for title in titles]
            
            threat_percentage, negative_titles, positive_titles = analyze_with_local_model(translated_titles)
            threats[country] = threat_percentage
            all_negative_titles.extend(negative_titles)
            all_positive_titles.extend(positive_titles)
            file.write(f"Threat Percentage: {threat_percentage:.2f}\n\n")
            
            for entry in daily_entries:
                file.write(f"Title: {entry.title}\n")
                file.write(f"Published Date: {entry.published}\n")
                file.write(f"Link: {entry.link}\n\n")
        else:
            threats[country] = 0.0
            file.write("No recent entries found.")
    
    print(f"File saved at: {file_path}")

# Multiply threat percentage by 1.5 for eligible countries
for country in ["Syria", "Russia", "Ukraine", "Iraq"]:
    if country in threats:
        threats[country] *= 1.0

# Calculate Turkey BNT index
total_threat = sum(threats.values())
number_of_countries = len(threats)
bnt_index = 0.0
if total_threat > 1.0:
    bnt_index = total_threat / 10
else:
    bnt_index = 1.0

# Ensure BNT Index matches the sum of contributions
threats["Turkey"] = bnt_index
total_threat = sum(threats.values())

print(f"\nTurkey BNT Index: {bnt_index:.2f}")

# Write threat contributions to Excel file
contributions_path = os.path.join(desktop_path, "threat_contributions.xlsx")
df = pd.DataFrame(list(threats.items()), columns=['Country', 'Contribution'])
df.loc[df['Country'].isin(["Syria", "Russia", "Ukraine", "Iraq"]), 'Contribution'] *= 1.0
df.loc[df['Country'] == "Turkey", 'Contribution'] = bnt_index

# Save to Excel
df.to_excel(contributions_path, index=False)

print(f"Threat contributions saved at: {contributions_path}")

# Write all negative and positive titles to txt files
negative_titles_path = os.path.join(desktop_path, "all_negative_titles.txt")
with open(negative_titles_path, "w", encoding="utf-8") as file:
    for title, contribution in all_negative_titles:
        file.write(f"Title: {title}\nContribution to threat points: {contribution}\n\n")

positive_titles_path = os.path.join(desktop_path, "all_positive_titles.txt")
with open(positive_titles_path, "w", encoding="utf-8") as file:
    for title, contribution in all_positive_titles:
        file.write(f"Title: {title}\nContribution to positive points: {contribution}\n\n")

print(f"Negative titles saved at: {negative_titles_path}")
print(f"Positive titles saved at: {positive_titles_path}")

# Read threat percentages from text files
threats_from_txt = {}
for country in rss_urls.keys():
    file_path = os.path.join(desktop_path, f"{country}_news.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                if "Threat Percentage:" in line:
                    threat_percentage = float(line.split(":")[1].strip())
                    threats_from_txt[country] = threat_percentage
                    break
    else:
        threats_from_txt[country] = 0.0

# Multiply threat percentage by 1.5 for eligible countries
for country in ["Syria", "Russia", "Ukraine", "Iraq"]:
    if country in threats_from_txt:
        threats_from_txt[country] *= 1.0

# Calculate Turkey BNT index from txt data
total_threat_from_txt = sum(threats_from_txt.values())
bnt_index_from_txt = 0.0
if total_threat_from_txt > 1.0:
    bnt_index_from_txt = total_threat_from_txt / 10
else:
    bnt_index_from_txt = 1.0

# Ensure BNT Index matches the sum of contributions
threats_from_txt["Turkey"] = bnt_index_from_txt

# Write threat contributions from txt data to Excel file
contributions_from_txt_path = os.path.join(desktop_path, "threat_contributions_from_txt.xlsx")
df_from_txt = pd.DataFrame(list(threats_from_txt.items()), columns=['Country', 'Contribution'])
df_from_txt.loc[df_from_txt['Country'].isin(["Syria", "Russia", "Ukraine", "Iraq"]), 'Contribution'] *= 1.0
df_from_txt.loc[df_from_txt['Country'] == "Turkey", 'Contribution'] = bnt_index_from_txt

# Save to Excel
df_from_txt.to_excel(contributions_from_txt_path, index=False)

print(f"Threat contributions from txt saved at: {contributions_from_txt_path}")