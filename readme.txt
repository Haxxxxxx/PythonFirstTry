# README

QUICK START GUIDE
=================

Overview
--------

This project combines a Jupyter Notebook and a Flask API to fetch and analyze data from the Blizzard Diablo III API.

**Important:** You must run the Flask API before using the notebook.

Setup Instructions
------------------

1. **Install Dependencies**

Ensure you have Python 3 installed. Then, install the required package,
If you don't have python type the first expression and then the second one: 

   conda install python
   pip install flask aiohttp asyncio python-dotenv flask-caching "Flask[async]"

2. **Set Up API Credentials**
Create a .env file in the project directory with your Blizzard API credentials:

\DO NOT SHARE THIS INFORMATIONS/
      BLIZZARD_CLIENT_ID=3350df6c6a7f42dfb0438c31bcbfad92
      BLIZZARD_CLIENT_SECRET=5L5cTL8QtWcKOSG5xIvyONsCtn4OMnH2

3. **Run the Flask API**
Start the API by running:

   python app.py

The API should now be running at http://localhost:5000/.

3. **Using the Jupyter Notebook**

    jupyter notebook

Open and Run the Notebook
Open the notebook file (DiabloIIIAnalysis.ipynb).

Run the cells sequentially.
The notebook will interact with the running Flask API.

**Important Notes**
API Must Be Running: The notebook depends on the Flask API. Ensure it's running to avoid errors.
Keep Credentials Secure: Do not share your .env file or Blizzard API credentials.
Dependencies: If you add new libraries, update your dependencies accordingly.
   