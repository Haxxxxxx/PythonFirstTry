import os
import aiohttp
import asyncio
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from flask_caching import Cache
from datetime import datetime, timedelta, timezone

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
token_expiry = datetime.now(timezone.utc)  # Initialize as timezone-aware

# Asynchronous function to authenticate and get OAuth2 token with expiry handling
async def get_oauth_token():
    global access_token, token_expiry
    # Ensure both datetime objects are timezone-aware
    if access_token and datetime.now(timezone.utc) < token_expiry:
        return access_token
    
    payload = {'grant_type': 'client_credentials'}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(AUTH_URL, auth=aiohttp.BasicAuth(CLIENT_ID, CLIENT_SECRET), data=payload) as response:
            if response.status == 200:
                token_data = await response.json()
                access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # default to 1 hour
                token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)  # timezone-aware
                return access_token
            else:
                raise Exception(f"Failed to get token: {response.status} - {await response.text()}")

# Asynchronous function to fetch general data from Blizzard API with caching
@cache.memoize(timeout=300)  # Cache for 5 minutes
async def fetch_data(url):
    token = await get_oauth_token()
    if not token:
        return {"error": "No access token available."}, 500

    headers = {'Authorization': f'Bearer {token}'}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                print(f"Fetching data from {url}")
                print(f"Response status code: {response.status}")
                response_data = await response.json()
                return response_data, response.status
        except aiohttp.ClientError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return {"error": str(http_err)}, 500
        except Exception as err:
            print(f"Other error occurred: {err}")
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
    
    if status_code != 200:
        return jsonify({"error": "Failed to fetch profile data."}), status_code

    heroes = profile_data.get('heroes', [])
    detailed_heroes = []
    for hero in heroes:
        hero_id = hero.get('id')
        if hero_id:
            items_url = f"https://{region}.api.blizzard.com/d3/profile/{account}/hero/{hero_id}/items?locale={locale}"
            items_data, _ = fetch_data(items_url)
            hero['items'] = items_data.get('items', {})
            detailed_heroes.append(hero)
    
    return jsonify({"heroes": detailed_heroes})


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
    # Fetch the profile data for the account
    # Render the page with the correct account data
    return render_template('character.html', account=account)



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


@app.route('/api/hero-class/<string:class_slug>/skills', methods=['GET'])
def get_class_skills(class_slug):
    region = request.args.get('region', default="us", type=str)
    locale = request.args.get('locale', default="en_US", type=str)
    url = f"https://{region}.api.blizzard.com/d3/data/hero/{class_slug}/skills?locale={locale}"
    
    skills_data, status_code = fetch_data(url)

    if status_code != 200:
        return jsonify({"error": "Failed to fetch skills data"}), status_code

    return jsonify(skills_data)


    
@app.route('/most_used')
def most_used_page():
    return render_template('most_used.html')


import random

@app.route('/api/most_used_items', methods=['GET'])
def get_most_used_items():
    season_id = request.args.get('season_id', default=23, type=int)
    class_slug = request.args.get('class_slug', default='rift-monk', type=str)

    print(f"Fetching most used items for Season {season_id}, Class: {class_slug}")

    # Fetch leaderboard data for the given class and season from Blizzard API
    url = f"https://us.api.blizzard.com/data/d3/season/{season_id}/leaderboard/{class_slug}?locale=en_US"
    leaderboard_data, status_code = fetch_data(url)  # Removed await

    if status_code != 200:
        print(f"Error fetching leaderboard: {leaderboard_data}")
        return jsonify({'error': 'Failed to fetch leaderboard data'}), status_code

    # Get top 15 players from the leaderboard
    rows = leaderboard_data.get('row', [])[:15]  # Fetch top 15 players

    item_occurrences = {}

    for row in rows:
        battle_tag = row.get('player', [{}])[0].get('data', [{}])[0].get('string')
        print(f"Processing BattleTag: {battle_tag}")
        if battle_tag:
            # Fetch character data using the battle_tag from the Blizzard API
            character_data = get_character_data(battle_tag)
            if 'heroes' not in character_data:
                continue  # Skip if no heroes data available

            # Process heroes for the selected class
            for hero in character_data['heroes']:
                if hero.get('classSlug') == class_slug.split('-')[-1]:  # Match class from the slug
                    print(f"Fetching items for hero: {hero.get('name')} (Class: {hero.get('classSlug')})")

                    # Fetch hero items using the hero ID
                    hero_id = hero.get('id')
                    hero_items = get_hero_items(battle_tag, hero_id)

                    # Log the hero_items response for debugging
                    print(f"Items for hero {hero.get('name')}: {hero_items}")

                    # Ensure we correctly access the items data
                    if hero_items:
                        for slot, item in hero_items.items():
                            item_name = item.get('name')
                            if item_name:
                                if slot not in item_occurrences:
                                    item_occurrences[slot] = {}
                                if item_name not in item_occurrences[slot]:
                                    item_occurrences[slot][item_name] = {
                                        "item": item,
                                        "count": 0
                                    }
                                item_occurrences[slot][item_name]["count"] += 1  # Count the occurrence of the item
                    else:
                        print(f"No items found for hero {hero.get('name')}.")
    
    # Find the most used item for each slot
    most_used_items = {
        slot: max(items.values(), key=lambda x: x['count'])
        for slot, items in item_occurrences.items()
    }

    print(f"Most used items: {most_used_items}")
    return jsonify(most_used_items)

# Fetch hero items using Blizzard API
def get_hero_items(battle_tag, hero_id):
    region = "us"
    locale = "en_US"
    battle_tag_formatted = battle_tag.replace("#", "-")  # Replace '#' with '-' for API compatibility
    url = f"https://{region}.api.blizzard.com/d3/profile/{battle_tag_formatted}/hero/{hero_id}/items?locale={locale}"
    hero_items_data, status_code = fetch_data(url)

    if status_code != 200:
        print(f"Error fetching hero items for {battle_tag}, Hero ID: {hero_id}")
        return {}
    
    return hero_items_data

# Fetch character data using Blizzard API
def get_character_data(battle_tag):
    region = "us"
    locale = "en_US"
    battle_tag_formatted = battle_tag.replace("#", "-")  # Replace '#' with '-' for API compatibility
    url = f"https://{region}.api.blizzard.com/d3/profile/{battle_tag_formatted}/?locale={locale}"
    character_data, status_code = fetch_data(url)

    if status_code != 200:
        print(f"Error fetching character data for {battle_tag}")
        return {}
    
    return character_data


# Start Flask app
if __name__ == '__main__':
    app.run(debug=True)


