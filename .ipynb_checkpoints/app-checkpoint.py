import os
import requests
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from flask_caching import Cache
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Blizzard API credentials
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

# Blizzard OAuth token endpoint
AUTH_URL = "https://oauth.battle.net/token"

# Global variables to store token and its expiry
access_token = None
token_expiry = datetime.utcnow()

# Function to authenticate and get OAuth2 token with expiry handling
def get_oauth_token():
    global access_token, token_expiry
    if access_token and datetime.utcnow() < token_expiry:
        return access_token
    
    payload = {'grant_type': 'client_credentials'}
    response = requests.post(AUTH_URL, auth=(CLIENT_ID, CLIENT_SECRET), data=payload)
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        expires_in = token_data.get('expires_in', 3600)  # default to 1 hour
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # refresh 1 minute before expiry
        return access_token
    else:
        raise Exception(f"Failed to get token: {response.status_code} - {response.text}")

# Function to fetch general data from Blizzard API with caching
@cache.memoize(timeout=300)  # Cache for 5 minutes
def fetch_data(url):
    token = get_oauth_token()
    if not token:
        return {"error": "No access token available."}, 500

    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return {"error": f"404 Not Found for URL: {url}"}, 404
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # Log HTTP errors
        return {"error": str(http_err)}, response.status_code
    except Exception as err:
        print(f"Other error occurred: {err}")  # Log other errors
        return {"error": str(err)}, 500

# Route to serve the home page
@app.route('/')
def home():
    return render_template('index.html')

# Route to fetch seasons data
@app.route('/api/seasons', methods=['GET'])
def get_seasons():
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/data/d3/season/?locale={locale}"
    seasons_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify(seasons_data), status_code
    
    return jsonify(seasons_data)

# Route to fetch leaderboard data by season and class
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    season_id = request.args.get('season_id', default=23, type=int)
    leaderboard_name = request.args.get('leaderboard_name', default="rift-barbarian", type=str)
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    
    url = f"https://{region}.api.blizzard.com/data/d3/season/{season_id}/leaderboard/{leaderboard_name}?locale={locale}"
    leaderboard_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify(leaderboard_data), status_code
    
    return jsonify(leaderboard_data)

# Route to fetch item details by item slug
@app.route('/api/item/<string:item_slug>', methods=['GET'])
def get_item(item_slug):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/item/{item_slug}?locale={locale}"
    item_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify(item_data), status_code
    
    return jsonify(item_data)

# Route to fetch full profile data by account, including heroes, items, and follower items
@app.route('/api/character/<string:account>', methods=['GET'])
def api_character(account):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/?locale={locale}"
    profile_data, status_code = fetch_data(url)
    
    if status_code != 200 or not isinstance(profile_data, dict):
        return jsonify({"error": "Failed to fetch profile data."}), status_code
    
    # Extract achievements if available
    achievements = profile_data.get('achievements', {}).get('completed', [])
    
    # Fetch items and follower items for each hero
    heroes = profile_data.get('heroes', [])
    detailed_heroes = []
    for hero in heroes:
        hero_id = hero.get('id')
        if hero_id:
            items_url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/items?locale={locale}"
            follower_items_url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/follower-items?locale={locale}"
            items_data, items_status = fetch_data(items_url)
            follower_items_data, follower_items_status = fetch_data(follower_items_url)
            hero['items'] = items_data if items_status == 200 else {}
            hero['follower_items'] = follower_items_data if follower_items_status == 200 else {}
            detailed_heroes.append(hero)
    
    # Include achievements and detailed heroes in the response
    response = {
        'profile': profile_data,
        'achievements': achievements,
        'heroes': detailed_heroes
    }
    return jsonify(response)

# Route to fetch detailed hero profile
@app.route('/api/character/<string:account>/hero/<int:hero_id>', methods=['GET'])
def get_hero(account, hero_id):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/?locale={locale}"
    hero_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify(hero_data), status_code
    
    return jsonify(hero_data)

# Route to fetch items for a specific hero
@app.route('/api/character/<string:account>/hero/<int:hero_id>/items', methods=['GET'])
def get_hero_items(account, hero_id):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/items?locale={locale}"
    items_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify({"error": "Failed to fetch hero items."}), status_code
    
    return jsonify(items_data)

# Route to fetch follower items for a specific hero
@app.route('/api/character/<string:account>/hero/<int:hero_id>/follower-items', methods=['GET'])
def get_follower_items(account, hero_id):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/follower-items?locale={locale}"
    follower_items_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify({"error": "Failed to fetch follower items."}), status_code
    
    return jsonify(follower_items_data)

# Route to fetch account profile data (optional)
@app.route('/api/account/<string:account>', methods=['GET'])
def get_account_profile(account):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/?locale={locale}"
    profile_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify(profile_data), status_code
    
    return jsonify(profile_data)

@app.route('/character/<string:account>', methods=['GET'])
def character_page(account):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)

    # Fetch character profile and heroes data
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/?locale={locale}"
    profile_data, status_code = fetch_data(url)

    if status_code != 200 or not isinstance(profile_data, dict):
        return render_template('error.html', message='Failed to load character profile'), status_code

    # Fetch detailed hero data including items and follower items
    heroes = profile_data.get('heroes', [])
    detailed_heroes = []
    for hero in heroes:
        hero_id = hero.get('id')
        if hero_id:
            items_url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/items?locale={locale}"
            items_data, items_status = fetch_data(items_url)
            hero['items'] = items_data if items_status == 200 else {}
            detailed_heroes.append(hero)

    # Pass account and profile data to the template
    return render_template('character.html', account=account, profile=profile_data, heroes=detailed_heroes)


# Route to fetch rift details
@app.route('/api/leaderboard_rift/<string:battletag>', methods=['GET'])
def get_rift_details(battletag):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    
    # Replace '#' with '-' to conform to API expectations
    account = battletag.replace('#', '-')
    
    # Assuming 'rift-barbarian' as the default leaderboard name for rift details
    season_id = request.args.get('season_id', default=23, type=int)
    leaderboard_name = "rift-barbarian"
    
    url = f"https://{region}.api.blizzard.com/data/d3/season/{season_id}/leaderboard/{leaderboard_name}?locale={locale}"
    rift_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify({"error": "Failed to fetch rift details."}), status_code
    
    return jsonify(rift_data)
# Route to fetch account achievements data
@app.route('/api/account/<string:account>/achievements', methods=['GET'])
def get_account_achievements(account):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/achievements?locale={locale}"
    achievements_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return jsonify({"error": "Failed to fetch achievements."}), status_code
    
    return jsonify(achievements_data)
@app.route('/character/<string:account>/item/<string:item_id>', methods=['GET'])
def item_page(account, item_id):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    
    # Fetch the item details from the API
    url = f"https://{region}.api.blizzard.com/d3/data/item/{item_id}?locale={locale}"
    item_data, status_code = fetch_data(url)
    
    if status_code != 200:
        return render_template('error.html', message='Item not found'), status_code

    # Render the item page template
    return render_template('item.html', account=account, item=item_data)

@app.route('/character/<string:account>/hero/<int:hero_id>/items', methods=['GET'])
def hero_items_page(account, hero_id):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)

    # Fetch hero's items
    url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/items?locale={locale}"
    items_data, status_code = fetch_data(url)

    if status_code != 200:
        return render_template('error.html', message="Unable to retrieve hero's items"), status_code

    # Render the items data in the template
    return render_template('item.html', account=account, hero_id=hero_id, items=items_data)

# Route to fetch acts data
@app.route('/api/acts', methods=['GET'])
def get_act_index():
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/act?locale={locale}"
    act_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify(act_data), status_code

    return jsonify(act_data)


# Route to fetch artisan data
@app.route('/api/artisan/<string:artisan_slug>', methods=['GET'])
def get_artisan(artisan_slug):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/artisan/{artisan_slug}?locale={locale}"
    artisan_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify(artisan_data), status_code

    return jsonify(artisan_data)

@app.route('/classes')
def classes():
    return render_template('classes.html')
# Route to fetch hero class data by slug
@app.route('/api/hero-class/<string:class_slug>', methods=['GET'])
def get_hero_class(class_slug):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/hero/{class_slug}?locale={locale}"
    hero_class_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify(hero_class_data), status_code

    return jsonify(hero_class_data)

# Route to fetch skill data by hero class and skill slug
@app.route('/api/hero-class/<string:class_slug>/skill/<string:skill_slug>', methods=['GET'])
def get_skill(class_slug, skill_slug):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/hero/{class_slug}/skill/{skill_slug}?locale={locale}"
    skill_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify(skill_data), status_code

    return jsonify(skill_data)

# Route to fetch all item types
@app.route('/api/item-types', methods=['GET'])
def get_item_types():
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/item-type?locale={locale}"
    item_types_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify(item_types_data), status_code

    return jsonify(item_types_data)


@app.route('/api/item-type/<string:item_type>', methods=['GET'])
def get_item_type(item_type):
    item_types = {
        "craftingplansmith": {"name": "Blacksmith Plan", "description": "A crafting plan used by the blacksmith."},
        "bootsbarbarian": {"name": "Barbarian Boots", "description": "Boots for a barbarian."},
        # Add more item types here...
    }

    if item_type in item_types:
        return jsonify(item_types[item_type])
    else:
        return jsonify({"error": "Item type not found"}), 404


@app.route('/api/hero-class/<string:hero_class>/skills', methods=['GET'])
def get_hero_class_skills(hero_class):
    skills_data = {
        "barbarian": {"skills": [{"slug": "bash", "name": "Bash"}, {"slug": "hammer-of-the-ancients", "name": "Hammer of the Ancients"}]},
        "wizard": {"skills": [{"slug": "magic-missile", "name": "Magic Missile"}, {"slug": "arcane-orb", "name": "Arcane Orb"}]},
        # Add more class skills here...
    }

    if hero_class in skills_data:
        return jsonify(skills_data[hero_class])
    else:
        return jsonify({"error": "Hero class not found"}), 404
# Example route to fetch item type details


# Start Flask app
if __name__ == '__main__':
    app.run(debug=True)
