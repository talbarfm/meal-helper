import requests
import random
from flask import Flask, render_template, jsonify, abort

app = Flask(__name__)


def get_recipe_for(main_ingredient: str) -> dict | None:
    """
    Fetch a random recipe with a specified main ingredient.
    The recipes are requested from "themealdb" API.
    """
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={main_ingredient}"
    response = requests.get(url)
    data = response.json()

    if not data.get("meals"):
        return None

    random_meal = random.choice(data["meals"])
    meal_id = random_meal["idMeal"]

    meal_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    response = requests.get(meal_url)
    meal_data = response.json()
    meal = meal_data["meals"][0]

    ingredients = {}
    for i in range(1, 21):
        ingredient = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ingredient and ingredient.strip():
            ingredients[ingredient.strip()] = (measure or "").strip()

    return dict(
        name=meal["strMeal"],
        image=meal["strMealThumb"],
        video=meal["strYoutube"],
        instructions=meal["strInstructions"],
        ingredients=ingredients,
    )


@app.route('/')
def index():
    """
    Renders and returns the main page HTML.
    """
    return render_template("index.html")


@app.route('/recipe/<ingredient>')
def recipe(ingredient):
    """
    Renders and returns an HTML page with a random recipe for a given main ingredient.
    """
    recipe_data = get_recipe_for(ingredient)
    if recipe_data is None:
        abort(404)

    return render_template("recipe.html",
                           ingredient=ingredient,
                           recipe=recipe_data)


@app.route('/recipe/<ingredient>/json')
def recipe_json(ingredient):
    """
    Returns a JSON with a random recipe for a given main ingredient.
    """
    recipe_data = get_recipe_for(ingredient)
    if recipe_data is None:
        abort(404)

    return jsonify(recipe_data)


if __name__ == '__main__':
    app.run(debug=True)