// Static JavaScript for Diablo III Project

const classImages = {
    "rift-barbarian": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/barbarian_male.png",
    "rift-wizard": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/wizard_female.png",
    "rift-dh": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/demonhunter_female.png",
    "rift-monk": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/monk_male.png",
    "rift-necromancer": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/p6_necro_male.png",
    "rift-wd": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/witchdoctor_male.png",
    "rift-crusader": "https://assets.diablo3.blizzard.com/d3/icons/portraits/42/x1_crusader_male.png",
    "all": "https://dvnv93bpfr08y.cloudfront.net/original/1X/21c1659096b0e44c76cdb7e17c859bf52dc8667d.png" // All Classes Image
};

const classNames = {
    "rift-barbarian": "Barbarian",
    "rift-wizard": "Wizard",
    "rift-dh": "Demon Hunter",
    "rift-monk": "Monk",
    "rift-necromancer": "Necromancer",
    "rift-wd": "Witch Doctor",
    "rift-crusader": "Crusader",
    "all": "All Classes"
};

const playersPerPage = 50;
let currentPage = 1;
let totalPages = 1;
let leaderboardData = [];
let filteredData = [];


//#region Index
function updateClassImage() {
    showLoader();  // Show the loader before filtering

    const classSlug = document.getElementById('class').value;
    if (classSlug !== 'all') {
        document.getElementById('classImage').src = classImages[classSlug];
    } else {
        document.getElementById('classImage').src = classImages['all'];
    }
}
// Fetch available seasons from the API
async function fetchSeasons() {
    showLoader();  // Show the loader before fetching

    try {
        const response = await fetch(`/api/seasons`);
        const data = await response.json();
        const seasonDropdown = document.getElementById('season');
        seasonDropdown.innerHTML = ''; // Clear previous options

        if (data.season && Array.isArray(data.season)) {
            data.season.forEach((season, index) => {
                const seasonId = index + 1;
                const option = document.createElement('option');
                option.value = seasonId;
                option.text = `Season ${seasonId}`;
                seasonDropdown.appendChild(option);
            });

            // Set current season to the last season in the list
            seasonDropdown.value = data.season.length;
            fetchLeaderboard();
        } else {
            console.error('Seasons data is not an array or undefined');
        }
    } catch (error) {
        console.error('Error fetching seasons:', error);
    }
}
// Fetch leaderboard data based on season and class
async function fetchLeaderboard() {
    const season = document.getElementById('season').value;
    const classSlug = document.getElementById('class').value;

    try {
        let data = [];
        if (classSlug === 'all') {
            // Fetch leaderboard for all classes
            const classes = ['rift-barbarian', 'rift-wizard', 'rift-dh', 'rift-monk', 'rift-necromancer', 'rift-wd', 'rift-crusader'];
            const promises = classes.map(async (cls) => {
                const res = await fetch(`/api/leaderboard?season_id=${season}&leaderboard_name=${cls}`);
                const leaderboardData = await res.json();
                const rows = leaderboardData.row || [];
                return rows.map(row => ({ ...row, classSlug: cls }));  // Add classSlug to each row
            });
            // Flatten the array of arrays
            const results = await Promise.all(promises);
            data = results.flat();
        } else {
            const response = await fetch(`/api/leaderboard?season_id=${season}&leaderboard_name=${classSlug}`);
            data = (await response.json()).row || [];
        }

        leaderboardData = data.sort((a, b) => {
            const riftLevelA = getRiftLevel(a);
            const riftTimeA = getRiftTime(a);
            const riftLevelB = getRiftLevel(b);
            const riftTimeB = getRiftTime(b);

            // Sort by rift level descending, and by rift time ascending (faster is better)
            if (riftLevelA !== riftLevelB) {
                return riftLevelB - riftLevelA;
            } else {
                return riftTimeA - riftTimeB;
            }
        });

        filteredData = leaderboardData;
        totalPages = Math.ceil(filteredData.length / playersPerPage);
        currentPage = 1;
        console.log(leaderboardData);
        displayLeaderboard(classSlug === 'all');  // Display the first page, and pass true if "all classes" is selected
    } catch (error) {
        console.error('Error fetching leaderboard:', error);
    }
}
// Sort leaderboard by rift level and rift time (higher rift level first, then by fastest time)
function sortLeaderboard(data) {
    return data.sort((a, b) => {
        const riftLevelA = getRiftLevel(a);
        const riftTimeA = getRiftTime(a);
        const riftLevelB = getRiftLevel(b);
        const riftTimeB = getRiftTime(b);

        // Sort by rift level descending, and by rift time ascending (faster is better)
        if (riftLevelA !== riftLevelB) {
            return riftLevelB - riftLevelA;
        } else {
            return riftTimeA - riftTimeB;
        }
    });
}
// Function to update table headers based on whether searching by class or all classes
function updateTableHeaders(isPlayerSearch) {
    const tableHead = document.getElementById('leaderboardTable').getElementsByTagName('thead')[0];
    tableHead.innerHTML = '';  // Clear previous headers

    const headerRow = tableHead.insertRow();
    headerRow.insertCell(0).innerText = 'Rank';
    headerRow.insertCell(1).innerText = 'BattleTag';
    headerRow.insertCell(2).innerText = 'Rift Level';
    headerRow.insertCell(3).innerText = 'Rift Time';
    headerRow.insertCell(4).innerText = 'Completed Time';

    if (isPlayerSearch) {
        headerRow.insertCell(5).innerText = 'Class';  // Add Class column for player search across all classes
    }
}
// Function to display leaderboard data with the optional "Class" column
function displayLeaderboard(isPlayerSearch = false) {
    showLoader();  // Show the loader before filtering

    setTimeout(() => {
        // Show the class column if "all" is selected or it's a player search
        const showClassColumn = isPlayerSearch || document.getElementById('class').value === 'all';

        updateTableHeaders(showClassColumn);  // Update headers based on search type and selected class

        const leaderboardTableBody = document.getElementById('leaderboardTable').getElementsByTagName('tbody')[0];
        leaderboardTableBody.innerHTML = '';  // Clear previous rows

        if (!filteredData || filteredData.length === 0) {
            console.error('No rows found in leaderboard data');
            leaderboardTableBody.innerHTML = `<tr><td colspan="${showClassColumn ? 6 : 5}">No data available.</td></tr>`;
            return;
        }

        // Sort the leaderboard data before displaying
        const sortedData = sortLeaderboard(filteredData);

        const startIndex = (currentPage - 1) * playersPerPage;
        const endIndex = Math.min(startIndex + playersPerPage, sortedData.length);
        const pageData = sortedData.slice(startIndex, endIndex);

        pageData.forEach(row => {
            const rank = row.data.find(d => d.id === 'Rank')?.number || 'Unknown';
            const battleTag = row.data.find(d => d.id === 'BattleTag')?.string || 'Unknown';
            const riftLevel = getRiftLevel(row);
            const riftTime = msToTime(getRiftTime(row));
            const completedTime = row.data.find(d => d.id === 'CompletedTime')?.timestamp
                ? new Date(row.data.find(d => d.id === 'CompletedTime').timestamp).toLocaleString()
                : 'N/A';
            const classUsed = classNames[row.classSlug] || 'Unknown';

            const newRow = leaderboardTableBody.insertRow();
            newRow.insertCell(0).innerText = rank;

            // Make BattleTag clickable to view character details
            const battleTagCell = newRow.insertCell(1);
            const battleTagLink = document.createElement('a');
            battleTagLink.href = "#";
            battleTagLink.innerText = battleTag;
            battleTagLink.onclick = function () { viewCharacterDetails(battleTag); return false; };
            battleTagCell.appendChild(battleTagLink);

            newRow.insertCell(2).innerText = riftLevel;
            newRow.insertCell(3).innerText = riftTime;
            newRow.insertCell(4).innerText = completedTime;

            if (showClassColumn) {
                newRow.insertCell(5).innerText = classUsed;
            }
        });

        updatePaginationControls();
        hideLoader();  // Hide the loader once done
    }, 500);  // Adjust the timeout as needed for a more realistic effect
}
// Pagination controls
function updatePaginationControls() {
    document.getElementById('pageIndicator').innerText = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage === totalPages;
}
// Change page
function changePage(direction) {
    if ((currentPage === 1 && direction === -1) || (currentPage === totalPages && direction === 1)) {
        return; // Prevent going out of bounds
    }
    currentPage += direction;
    displayLeaderboard();  // Display leaderboard again after page change
}
// Search player by BattleTag
function searchPlayer() {
    const searchQuery = document.getElementById('playerSearch').value.toLowerCase();
    document.getElementById('class').value = 'all';  // Ensure class is set to "all" during player search

    if (!searchQuery) {
        // If no search query, reset to show all players
        filteredData = leaderboardData;
        displayLeaderboard(true);  // Call the function with true to ensure class column is shown
    } else {
        filteredData = leaderboardData.filter(row => {
            const battleTag = row.data.find(d => d.id === 'BattleTag')?.string.toLowerCase();
            return battleTag && battleTag.includes(searchQuery);
        });

        // Search across all classes, and always show the class column
        displayLeaderboard(true);  // Call the function with true to indicate it's a player search across all classes
    }

    totalPages = Math.ceil(filteredData.length / playersPerPage);
    currentPage = 1;
    displayLeaderboard(true);  // Ensure that the class column is displayed when searching
}
// Fetch and populate acts in the dropdown
async function fetchActs() {
    try {
        const response = await fetch('/api/acts');  // Call the Flask API endpoint
        const data = await response.json();  // Parse JSON response
        console.log("Acts Data:", data);  // Log the acts data to inspect its structure

        if (!data || !data.acts) {
            throw new Error('Acts data is undefined or not in the expected format');
        }

        const actsDropdown = document.getElementById('actsDropdown');
        actsDropdown.innerHTML = ''; // Clear previous options

        // Populate the dropdown with acts
        data.acts.forEach(act => {
            const option = document.createElement('option');
            option.value = act.number;  // Use act number as the value
            option.textContent = `Act ${act.number}: ${act.name}`;  // Display act name
            actsDropdown.appendChild(option);
        });

        // Automatically display quests for the first act on load
        if (data.acts.length > 0) {
            displayQuests(data.acts[0].quests);  // Show quests for the first act
        }

        // Add an event listener to handle act selection changes
        actsDropdown.addEventListener('change', function () {
            const selectedAct = data.acts.find(act => act.number == actsDropdown.value);
            displayQuests(selectedAct.quests);  // Show quests for the selected act
        });

    } catch (error) {
        console.error('Error fetching acts:', error);
    }
}
// Display quests for the selected act
function displayQuests(quests) {
    const questsList = document.getElementById('questsList');
    questsList.innerHTML = ''; // Clear previous quests

    quests.forEach(quest => {
        const li = document.createElement('li');
        li.textContent = `${quest.name}`;  // Display the quest name
        questsList.appendChild(li);
    });
}
// Display recipes with a "Show More" button if there are more than 20 recipes
function displayLimitedRecipes(listElement, recipes, recipeType) {
    const maxDisplayCount = 5; // Number of recipes to show initially
    listElement.innerHTML = ''; // Clear previous content

    // Display only the first 20 recipes
    recipes.slice(0, maxDisplayCount).forEach(recipe => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${recipe.name}</strong> - Cost: ${recipe.cost}`;
        listElement.appendChild(li);
    });

    // If there are more than 20 recipes, add a "Show More" button
    if (recipes.length > maxDisplayCount) {
        const showMoreButton = document.createElement('button');
        showMoreButton.textContent = `Show More ${recipeType}`;
        showMoreButton.onclick = function () {
            // Display the rest of the recipes
            recipes.slice(maxDisplayCount).forEach(recipe => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${recipe.name}</strong> - Cost: ${recipe.cost}`;
                listElement.appendChild(li);
            });

            // Remove the button after displaying all the recipes
            showMoreButton.style.display = 'none';
        };
        listElement.appendChild(showMoreButton);
    }
}
// Fetch and populate artisan tiers in the dropdown
async function fetchArtisan(artisanSlug) {
    try {
        const response = await fetch(`/api/artisan/${artisanSlug}`);
        const data = await response.json();
        console.log("Artisan Data:", data);

        if (!data || !data.training || !data.training.tiers) {
            throw new Error('Artisan training tiers data is undefined or not in the expected format');
        }

        const artisanTierDropdown = document.getElementById('artisanTierDropdown');
        artisanTierDropdown.innerHTML = ''; // Clear previous options

        data.training.tiers.forEach(tier => {
            const option = document.createElement('option');
            option.value = tier.tier;
            option.textContent = `Tier ${tier.tier}`;
            artisanTierDropdown.appendChild(option);
        });

        // Automatically fetch recipes for the first tier on load
        if (data.training.tiers.length > 0) {
            displayRecipesForTier(data.training.tiers[0]);
        }

        artisanTierDropdown.addEventListener('change', function () {
            const selectedTier = data.training.tiers.find(tier => tier.tier == artisanTierDropdown.value);
            displayRecipesForTier(selectedTier);
        });

    } catch (error) {
        console.error('Error fetching artisan data:', error);
    }
}
// Display recipes for the selected artisan tier
function displayRecipesForTier(tier) {
    const taughtRecipesList = document.getElementById('taughtRecipesList');
    const trainedRecipesList = document.getElementById('trainedRecipesList');

    taughtRecipesList.innerHTML = ''; // Clear previous taught recipes
    trainedRecipesList.innerHTML = ''; // Clear previous trained recipes

    // Limit to 20 recipes initially and provide a show more option
    displayLimitedRecipes(taughtRecipesList, tier.taughtRecipes, 'Taught Recipes');
    displayLimitedRecipes(trainedRecipesList, tier.trainedRecipes, 'Trained Recipes');
}
// Function to fetch Rift details (from leaderboard cache)
async function fetchRiftDetails(account) {
    const battleTag = account.replace('-', '#'); // Reverse the replacement
    // Assuming 'rift-barbarian' as the default leaderboard name for rift details
    const season_id = 23; // Adjust if necessary
    const leaderboard_name = "rift-barbarian";

    try {
        const response = await fetch(`/api/leaderboard?season_id=${season_id}&leaderboard_name=${encodeURIComponent(leaderboard_name)}`);
        if (!response.ok) {
            console.warn('Rift details not found for this user.');
            return {};
        }
        const riftData = await response.json();
        return riftData;
    } catch (error) {
        console.error('Error fetching rift details:', error);
        return {};
    }
}
//#endregion
//#region ITEM
// Helper function to generate HTML for items
function getItemHTML(items) {
    if (!items) return '<li>No items found</li>';

    return Object.keys(items).map(slot => {
        const item = items[slot];
        return `<li><strong>${slot}:</strong> ${item.name}</li>`;
    }).join('');
}
// Helper function to generate HTML for companion items
function getCompanionHTML(companion) {
    if (!companion || !companion.items) return '<li>No companion items found</li>';

    return Object.keys(companion.items).map(slot => {
        const item = companion.items[slot];
        return `<li><strong>${slot}:</strong> ${item.name}</li>`;
    }).join('');
}

//#endregion
//#region Classes
async function fetchHeroSkills() {
    const heroClass = document.getElementById('heroClassDropdown').value;
    if (!heroClass) return;

    try {
        // Fetch hero class details
        const classResponse = await fetch(`/api/hero-class/${heroClass}`);
        const classData = await classResponse.json();

        console.log("Class Data:", classData); // For debugging

        // Display class details
        const heroClassDetailsDiv = document.getElementById('heroClassDetails');
        heroClassDetailsDiv.innerHTML = `
            <h3>${classData.name || 'Unknown Class'}</h3>
            <p>${classData.description || 'No description available'}</p>
        `;

        // Populate the active skills dropdown
        const heroActiveSkillDropdown = document.getElementById('heroActiveSkillDropdown');
        heroActiveSkillDropdown.innerHTML = '<option value="">Select an Active Skill</option>'; // Clear previous options

        classData.skills.active.forEach(skill => {
            const option = document.createElement('option');
            option.value = skill.slug;
            option.textContent = skill.name;
            heroActiveSkillDropdown.appendChild(option);
        });

        // Populate the passive skills dropdown
        const heroPassiveSkillDropdown = document.getElementById('heroPassiveSkillDropdown');
        heroPassiveSkillDropdown.innerHTML = '<option value="">Select a Passive Skill</option>'; // Clear previous options

        classData.skills.passive.forEach(skill => {
            const option = document.createElement('option');
            option.value = skill.slug;
            option.textContent = skill.name;
            heroPassiveSkillDropdown.appendChild(option);
        });

    } catch (error) {
        console.error('Error fetching hero class or skills:', error);
    }
}
// Fetch and display skill details when selected
async function fetchHeroSkillDetails(skillType) {
    const heroClass = document.getElementById('heroClassDropdown').value;
    const skillDropdown = skillType === 'active' ? 'heroActiveSkillDropdown' : 'heroPassiveSkillDropdown';
    const heroSkill = document.getElementById(skillDropdown).value;
    if (!heroSkill) return;

    try {
        // Fetch the skill details
        const response = await fetch(`/api/hero-class/${heroClass}/skill/${heroSkill}`);
        const skillData = await response.json();
        
        console.log("Skill Data:", skillData); // For debugging

        // Display the skill details
        const heroSkillDetailsDiv = document.getElementById(
            skillType === 'active' ? 'heroActiveSkillDetails' : 'heroPassiveSkillDetails'
        );
        
        heroSkillDetailsDiv.innerHTML = `
            <h3>${skillData.skill?.name || 'Unknown Skill'}</h3>
            <p>${skillData.skill?.description || 'No description available'}</p>
        `;
        
        // Display runes if available
        if (skillData.runes && skillData.runes.length > 0) {
            const runesHtml = skillData.runes.map(rune => `
                <div>
                    <h4>${rune.name} (Level ${rune.level})</h4>
                    <p>${rune.descriptionHtml || rune.description}</p>
                </div>
            `).join('');
            heroSkillDetailsDiv.innerHTML += runesHtml;
        }

    } catch (error) {
        console.error('Error fetching skill details:', error);
    }
}
// Fetch and display item types in the dropdown
async function fetchItemTypes() {
    try {
        const response = await fetch('/api/item-types');
        const itemTypesData = await response.json();
        console.log(itemTypesData);  // Debugging to see the returned data

        // Check if data is in the expected format (Array)
        if (Array.isArray(itemTypesData)) {
            const itemTypesDropdown = document.getElementById('itemTypesDropdown');
            itemTypesDropdown.innerHTML = '<option value="">Select an Item Type</option>';

            // Create a Map to store unique item types (keyed by item name or id)
            const uniqueItems = new Map();

            // Populate the dropdown with unique item types
            itemTypesData.forEach(itemType => {
                if (!uniqueItems.has(itemType.name)) {  // Check if item type is already added by name
                    uniqueItems.set(itemType.name, itemType);  // Store in Map using name as the key
                    const option = document.createElement('option');
                    option.value = itemType.id;  // Use 'id' for the item type
                    option.textContent = itemType.name;  // Display the item type name in the dropdown
                    itemTypesDropdown.appendChild(option);
                }
            });
        } else {
            console.error("Unexpected data format. Expected an array.");
        }
    } catch (error) {
        console.error('Error fetching item types:', error);
    }
}
// Fetch and display item type details when an item is selected
async function fetchItemTypeDetails() {
    const itemType = document.getElementById('itemTypesDropdown').value;
    if (!itemType) return;  // If no item type is selected, exit the function

    try {
        const response = await fetch(`/api/item-type/${itemType}`);
        const itemTypeData = await response.json();
        console.log(itemTypeData);  // Debugging to see the returned item data

        // Display the item type details in the HTML
        const itemTypeDetailsDiv = document.getElementById('itemTypeDetails');
        if (itemTypeData.error) {
            itemTypeDetailsDiv.innerHTML = `<p>${itemTypeData.error}</p>`;
        } else {
            // Displaying item type and related items
            itemTypeDetailsDiv.innerHTML = `
                <h3>${itemTypeData.name}</h3>
                <p>${itemTypeData.description || 'No description available'}</p>
            `;
        }
    } catch (error) {
        console.error('Error fetching item type details:', error);
    }
}

//#endregion
//#region Character
async function fetchCharacterDetails(account) {
    try {
        const [profileResponse, accountProfileResponse] = await Promise.all([
            fetch(`/api/character/${encodeURIComponent(account)}`),
            fetch(`/api/account/${encodeURIComponent(account)}`)
        ]);

        if (!profileResponse.ok || !accountProfileResponse.ok) {
            throw new Error("Failed to fetch character or account data");
        }

        const profileData = await profileResponse.json();
        const accountProfileData = await accountProfileResponse.json();

        console.log("Profile Data:", accountProfileData);  // Debugging output

        // Check if heroes exist in the profile data
        if (!profileData.heroes || profileData.heroes.length === 0) {
            throw new Error("No heroes found in profile data");
        }

        // Display account profile information
        displayAccountProfile(accountProfileData);

        // Pass the account and heroes data to displayHeroDetails
        displayHeroDetails(profileData.heroes, account);  // Pass account to this function

    } catch (error) {
        console.error('Error fetching character details:', error);
        document.getElementById('heroDetails').innerHTML = '<p>Error loading character details.</p>';
    } finally {
        document.getElementById('profileLoader').style.display = 'none';
    }
}

function displayAccountProfile(profile) {
    // Check if profile has the expected properties
    if (!profile || !profile.battleTag) {
        console.error("Invalid profile data", profile);
        return;
    }

    const profileContainer = document.getElementById('accountProfile');
    profileContainer.innerHTML = `
        <h2>Account Profile</h2>
        <p><strong>BattleTag:</strong> ${profile.battleTag || 'N/A'}</p>
        <p><strong>Guild:</strong> ${profile.guildName || 'No Guild'}</p>
        <p><strong>Region:</strong> ${profile.region || 'N/A'}</p>
        <p><strong>Last Played:</strong> ${profile.lastPlayed ? new Date(profile.lastPlayed).toLocaleString() : 'N/A'}</p>
        <p><strong>Created At:</strong> ${profile.createdAt ? new Date(profile.createdAt).toLocaleString() : 'N/A'}</p>
        <p><strong>Paragon Level:</strong> ${profile.paragonLevel || 'N/A'}</p>
        <p><strong>Blacksmith Level:</strong> ${profile.blacksmith?.level || 'N/A'}</p>
        <p><strong>Jeweler Level:</strong> ${profile.jeweler?.level || 'N/A'}</p>
        <p><strong>Mystic Level:</strong> ${profile.mystic?.level || 'N/A'}</p>
        <p><strong>Highest Hardcore Level:</strong> ${profile.highestHardcoreLevel || 'N/A'}</p>
        <p><strong>Kills (Elites):</strong> ${profile.kills?.elites || 'N/A'}</p>
    `;
}

function displayHeroDetails(heroDetails, account) {
    const detailsContainer = document.getElementById('heroDetails');

    if (!detailsContainer) {
        console.error("Hero details container not found");
        return;
    }

    detailsContainer.innerHTML = '';  // Clear previous details

    if (heroDetails.length === 0) {
        detailsContainer.innerHTML = '<p>No heroes found for this account.</p>';
        return;
    }

    heroDetails.forEach(hero => {
        // Create a card for each hero
        const heroDiv = document.createElement('div');
        heroDiv.classList.add('hero-card');  // Add a CSS class for styling

        // Generate a clickable link for the hero's name
        heroDiv.innerHTML = `
            <h2><a href="/character/${account}/hero/${hero.id}/items" class="hero-link">${hero.name || 'Unnamed Hero'}</a> (Level ${hero.level})</h2>
            <p>Class: ${hero.class}</p>
            <p>Paragon Level: ${hero.paragonLevel}</p>
            <p>Kills: ${hero.kills?.elites || 0} elites</p>
            <p>Status: ${hero.dead ? 'Dead' : 'Alive'}</p>
        `;

        // Append the card to the container
        detailsContainer.appendChild(heroDiv);
    });

    detailsContainer.style.display = 'flex';  // Ensure the container is displayed
}

// Function to display account achievements
function displayAccountAchievements(achievements) {
    const achievementsContainer = document.getElementById('accountAchievements');
    if (!achievements || achievements.length === 0) {
        achievementsContainer.innerHTML = `<h2>Achievements</h2><p>No achievements found.</p>`;
    } else {
        let achievementsHTML = `<h2>Achievements</h2><ul>`;
        achievements.forEach(achievement => {
            achievementsHTML += `
                <li>
                    <strong>${achievement.title}</strong><br>
                    ${achievement.description}<br>
                    <em>Completed on: ${achievement.dateCompleted ? new Date(achievement.dateCompleted).toLocaleDateString() : 'N/A'}</em>
                </li>
            `;
        });
        achievementsHTML += `</ul>`;
        achievementsContainer.innerHTML = achievementsHTML;
    }
    achievementsContainer.style.display = 'block';
}
// Helper functions to extract rift level and time
function getRiftLevel(row) {
    const riftLevel = row.data.find(d => d.id === 'RiftLevel')?.number;
    return riftLevel || 0;
}
function getRiftTime(row) {
    const riftTime = row.data.find(d => d.id === 'RiftTime')?.timestamp;
    return riftTime || 0;
}
// Function to view character details
async function viewCharacterDetails(battleTag) {
    const account = battleTag.replace('#', '-');  // Blizzard API uses "-" instead of "#"
    window.location.href = `/character/${encodeURIComponent(account)}`;
}

//#endregion


// Function to show the loader
function showLoader() {
    const loader = document.getElementById("loader");
    if (loader) {
        loader.style.display = "block";
    }
    const table = document.getElementById("leaderboardTable");
    if (table) {
        table.style.display = "none";
    }
}
// Function to hide the loader
function hideLoader() {
    const loader = document.getElementById("loader");
    if (loader) {
        loader.style.display = "none";
    }
    const table = document.getElementById("leaderboardTable");
    if (table) {
        table.style.display = "";
    }
}
// Convert milliseconds to human-readable time
function msToTime(duration) {
    if (duration === 'N/A') return duration;

    const milliseconds = parseInt((duration % 1000) / 100),
        seconds = Math.floor((duration / 1000) % 60),
        minutes = Math.floor((duration / (1000 * 60)) % 60),
        hours = Math.floor((duration / (1000 * 60 * 60)) % 24);

    return (hours > 0 ? hours + "h " : "") + (minutes > 0 ? minutes + "m " : "") + (seconds > 0 ? seconds + "s" : "");
}
// Example: Fetching and displaying the profile and achievements
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const account = '{{ account }}';  // This is injected from the backend
        const profileResponse = await fetch(`/api/character/${account}`);
        const profileData = await profileResponse.json();
        
        displayAccountProfile(profileData.profile);
        displayAccountAchievements(profileData.achievements);
    } catch (error) {
        console.error('Error fetching character details:', error);
    } finally {
        document.getElementById('profileLoader').style.display = 'none';
    }
});
// Initialize the page by fetching seasons or character details based on the current page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('leaderboardTable')) {
        // We are on the home page
        fetchSeasons();
        updateClassImage();
    } else if (document.getElementById('profileLoader')) {
        // We are on the character details page
        const account = window.location.pathname.split('/').pop();
        fetchCharacterDetails(account);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('profileLoader')) {
        const account = window.location.pathname.split('/').pop();  // Get account from URL path
        fetchCharacterDetails(account);  // Pass the account to the fetch function
    }
});
// Call functions to populate dropdowns on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchItemTypes();
});
