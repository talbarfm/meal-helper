import requests
from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)


def get_recipe_for(main_ingredient: str) -> dict:
    """
    Fetch a random recipe with a specified main ingredient.
    The recipes are requested from "themealdb" API.
    """
    # YOUR CODE HERE:
    # 1. Use `requests` to fetch a list of recipes with `main_ingredient`
    #    - Here is a useful URL: https://www.themealdb.com/api/json/v1/1/filter.php?i=chicken_breast
    #    - Hint: `response.json()`
    # 2. Choose a random recipe from the list
    #    - Hint: `random.choice()`
    # 3. Use `requests` again to fetch the full recipe instructions
    #    - Here is another useful URL: https://www.themealdb.com/api/json/v1/1/lookup.php?i=52772
    # 4. Fill in the details of the returned object in the format below
    l = requests.get(f"https://www.themealdb.com/api/json/v1/1/filter.php?i={main_ingredient}").json()
    if not l["meals"]:
        return None
    rand_index=random.choice(l["meals"])["idMeal"]
    a= requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={rand_index}").json()
    meal = a["meals"][0]

    ingredients = {}
    for i in range(1, 21):
        ing_name = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ing_name and ing_name.strip():
            ingredients[ing_name] = measure

    return dict(
        name=meal["strMeal"],
        image=meal["strMealThumb"],
        video=meal["strYoutube"],
        instructions=meal["strInstructions"],
        ingredients=ingredients
    )


@app.route('/')
def index():
    """
    Renders and returns the main page HTML.
    """
    return render_template("index.html")


# YOUR CODE HERE:
# Make this endpoint get called when for the following routes: "/recipe/<ingredient>"
@app.route('/recipe/<ingredient>')
def recipe(ingredient):
    """
    Renders and returns an HTML page with a random recipe for a given main ingredient.
    """
    # BONUS:
    # If there are no meals for a given ingredient, return a 404 NOT FOUND error response.
    # Hint: Read the documentation of flask. This is a bonus :P
    recipe_data = get_recipe_for(ingredient)
    if recipe_data is None:
        return "Recipe not found", 404
    return render_template("recipe.html",
                           ingredient=ingredient,
                           recipe=recipe_data)


# YOU CODE HERE:
# Add another endpoint:
# Route "/recipe/<ingredient>/json" should return a JSON with the output of `get_recipe_for`.
# Hint: `flask.jsonify()`
@app.route('/recipe/<ingredient>/json')
def recipe_json(ingredient):
    recipe_data = get_recipe_for(ingredient)
    if recipe_data is None:
        return jsonify({"error": "No recipes found"}), 404
    return jsonify(recipe_data)


# BONUS:
# Add these endpoints:
# 1. "/personal" with POST method:
#    - Receives a recipe JSON in the request body, and adds it to a list of personal recipes.
#    - Make the list persistent in a JSON file.
#    - Redirect the client to the page of the newly saved recipe.
#    - Hint: `flask.request`
#    - Hint 2: `flask.redirect`
#    - Hint 3: Use `requests` to check if it works.
# 2. "/personal/<name>/<int:json>" with GET method:
#    - Returns the recipe page if `json == 0`, or a JSON if `json == 1`.
#    - Return a 404 response for flag values other than 0 or 1.
# 3. "/personal/<name>" with DELETE method:
#    - Delete the recipe with the given name
# 4. "/personal/all" with GET method:
#    - Returns a JSON with the list of personal recipes.



# EXTRA BONUS:
# Change the "/recipe" endpoints above to search the personal list as well.

if __name__ == '__main__':
    app.run(debug=True)
