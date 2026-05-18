import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

PATRIOT_LEAGUE_SCORING = {
    'V8 Grand Final':   {1: 180, 2: 160, 3: 140, 4: 120, 5: 100, 6: 80},
    'V8 Petite Final':  {1: 60,  2: 40,  3: 20},
    '2V8 Grand Final':  {1: 90,  2: 80,  3: 70,  4: 60,  5: 50,  6: 40},
    '2V8 Petite Final': {1: 30,  2: 20,  3: 10},
    'V4 Grand Final':   {1: 45,  2: 40,  3: 35,  4: 30,  5: 25,  6: 20},
    'V4 Petite Final':  {1: 15,  2: 10,  3: 5},
    '2V4 Grand Final':  {1: 4.5, 2: 4,   3: 3.5, 4: 3,   5: 2.5, 6: 2},
    '2V4 Petite Final': {1: 1.5, 2: 1,   3: 0.5},
}

CONFERENCES = {
    'patriot_league': {
        'name': 'Patriot League',
        'url': 'https://results.regattatiming.com/backoffice/webpages/results/summary.jsp?raceId=635',
        'scoring': PATRIOT_LEAGUE_SCORING,
    }
}

RACE_KEYWORDS = {
    'V8 Grand Final':   ['v8 grand', 'varsity eight grand', 'varsity 8 grand', 'v8 grand final'],
    'V8 Petite Final':  ['v8 petite', 'varsity eight petite', 'varsity 8 petite', 'v8 petite final'],
    '2V8 Grand Final':  ['2v8 grand', 'second varsity eight grand', 'jv eight grand', '2v8 grand final'],
    '2V8 Petite Final': ['2v8 petite', 'second varsity eight petite', 'jv eight petite', '2v8 petite final'],
    'V4 Grand Final':   ['v4 grand', 'varsity four grand', 'varsity 4 grand', 'v4 grand final'],
    'V4 Petite Final':  ['v4 petite', 'varsity four petite', 'varsity 4 petite', 'v4 petite final'],
    '2V4 Grand Final':  ['2v4 grand', 'second varsity four grand', 'jv four grand', '2v4 grand final'],
    '2V4 Petite Final': ['2v4 petite', 'second varsity four petite', 'jv four petite', '2v4 petite final'],
}

def match_race_name(text):
    text_lower = text.lower().strip()
    for race_name, keywords in RACE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return race_name
    return None

def scrape_conference(conf_key):
    conf = CONFERENCES[conf_key]
    url = conf['url']
    scoring = conf['scoring']
    debug_log = []
    team_scores = {}
    race_results_found = {}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    try:
        session.get("https://results.regattatiming.com", timeout=20)
        response = session.get(url, timeout=20)
        response.raise_for_status()
        debug_log.append("SUCCESS: Fetched " + url)
        debug_log.append("Status code: " + str(response.status_code))
    except Exception as e:
        debug_log.append("ERROR fetching page: " + str(e))
        return {
            'conference': conf['name'],
            'scores': {},
            'race_results': {},
            'debug': debug_log,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e)
        }

    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string if soup.title else 'No title found'
    debug_log.append("Page title: " + str(title))

    debug_log.append("=== ALL HEADINGS ===")
    for tag in soup.find_all(['h1','h2','h3','h4','h5','h6','b','strong']):
        text = tag.get_text(strip=True)
        if text and len(text) > 2:
            debug_log.append(tag.name + ": " + text[:150])

    tables = soup.find_all('table')
    debug_log.append("=== FOUND " + str(len(tables)) + " TABLES ===")

    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if not rows:
            continue

        debug_log.append("--- Table " + str(i+1) + " (" + str(len(rows)) + " rows) ---")
        race_name = None

        caption = table.find('caption')
        if caption:
            cap_text = caption.get_text(strip=True)
            debug_log.append("  Caption: " + cap_text)
            race_name = match_race_name(cap_text)

        for tag_name in ['h1','h2','h3','h4','h5','b','strong']:
            prev = table.find_previous(tag_name)
            if prev:
                prev_text = prev.get_text(strip=True)
                if prev_text and len(prev_text) < 200:
                    debug_log.append("  Prev " + tag_name + ": " + prev_text)
                    if not race_name:
                        race_name = match_race_name(prev_text)

        for j, row in enumerate(rows[:6]):
            cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
            if any(cells):
                debug_log.append("  Row " + str(j+1) + ": " + str(cells))

        if race_name:
            debug_log.append("  MATCHED RACE: " + race_name)
            results = []
            for row in rows:
                cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
                if cells and any(cells):
                    results.append(cells)
            race_results_found[race_name] = results

    for race_name, rows in race_results_found.items():
        scoring_table = scoring.get(race_name, {})
        if not scoring_table:
            continue

        place = 1
        max_place = max(scoring_table.keys())

        for row in rows:
            if not any(row):
                continue
            if place > max_place:
                break

            team = None
            for cell in row:
                if cell and len(cell) > 1 and not cell.replace('.','').replace(':','').isdigit():
                    team = cell
                    break

            if team and place in scoring_table:
                points = scoring_table[place]
                team_scores[team] = team_scores.get(team, 0) + points
                debug_log.append("SCORED: " + team + " | " + race_name + " | Place " + str(place) + " | " + str(points) + " pts")
                place += 1

    sorted_scores = dict(sorted(team_scores.items(), key=lambda x: x[1], reverse=True))

    return {
        'conference': conf['name'],
        'scores': sorted_scores,
        'race_results': race_results_found,
        'debug': debug_log,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

def scrape_all():
    all_data = {}
    for conf_key in CONFERENCES:
        print("Scraping " + conf_key + "...")
        all_data[conf_key] = scrape_conference(conf_key)
        print("Scores: " + str(all_data[conf_key]['scores']))

    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scores.json')
    with open(data_path, 'w') as f:
        json.dump(all_data, f, indent=2)

    print("Saved to " + data_path)
    return all_data

if __name__ == '__main__':
    scrape_all()
