import json
import random
from pathlib import Path

import requests
from flask import Flask, render_template, jsonify, abort, request, redirect, url_for

app = Flask(__name__)

API_URL = "https://www.themealdb.com/api/json/v1/1"
PERSONAL_FILE = Path(__file__).with_name("personal_recipes.json")


def fetch_meal(meal_id: str) -> dict:
    """
    Fetches the full recipe of a meal from "themealdb" API and converts it to our recipe format.
    """
    response = requests.get(f"{API_URL}/lookup.php", params={"i": meal_id}, timeout=10)
    response.raise_for_status()
    meal = response.json()["meals"][0]

    # Pair strIngredientN with strMeasureN, skipping empty slots ("" or None)
    ingredients = {}
    for i in range(1, 21):
        ingredient = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if ingredient:
            ingredients[ingredient] = measure

    return dict(
        name=(meal["strMeal"] or "").strip(),
        image=meal["strMealThumb"] or "",
        video=meal["strYoutube"] or "",
        instructions=meal["strInstructions"] or "",
        ingredients=ingredients,
    )


def personal_with_ingredient(main_ingredient: str) -> list:
    """
    Returns the personal recipes that contain `main_ingredient` (case-insensitive, "_" == " ").
    """
    wanted = main_ingredient.replace("_", " ").strip().lower()
    return [r for r in load_personal()
            if wanted in (name.lower() for name in r["ingredients"])]


def get_recipe_for(main_ingredient: str):
    """
    Fetch a random recipe with a specified main ingredient.
    The recipes are requested from "themealdb" API, and the personal recipes are searched too.
    Returns None if no recipe contains the ingredient.
    """
    # 1. Fetch the list of meals that use `main_ingredient`
    response = requests.get(f"{API_URL}/filter.php", params={"i": main_ingredient}, timeout=10)
    response.raise_for_status()
    api_meals = response.json()["meals"] or []  # The API returns {"meals": null} when nothing matches

    # 2. Choose a random recipe out of both sources, each recipe with the same chance
    candidates = [("api", meal["idMeal"]) for meal in api_meals]
    candidates += [("personal", recipe) for recipe in personal_with_ingredient(main_ingredient)]
    if not candidates:
        return None
    source, choice = random.choice(candidates)

    # 3. Personal recipes are already complete; API meals need a second request
    if source == "personal":
        return choice
    return fetch_meal(choice)


@app.route('/')
def index():
    """
    Renders and returns the main page HTML.
    """
    return render_template("index.html")


@app.route("/recipe/<ingredient>")
def recipe(ingredient):
    """
    Renders and returns an HTML page with a random recipe for a given main ingredient.
    """
    meal = get_recipe_for(ingredient)
    if meal is None:
        abort(404, description=f"No recipes found with {ingredient!r}.")
    return render_template("recipe.html", ingredient=ingredient, recipe=meal)


@app.route("/recipe/<ingredient>/json")
def recipe_json(ingredient):
    """
    Returns a random recipe for a given main ingredient as JSON.
    """
    meal = get_recipe_for(ingredient)
    if meal is None:
        abort(404, description=f"No recipes found with {ingredient!r}.")
    return jsonify(meal)


def load_personal() -> list:
    """
    Reads the personal recipes list from the JSON file (empty list if there is no file yet).
    """
    if not PERSONAL_FILE.exists():
        return []
    with PERSONAL_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def save_personal(recipes: list) -> None:
    """
    Writes the personal recipes list to the JSON file.
    Writes to a temporary file first, so a crash never leaves a half-written file.
    """
    temp_file = PERSONAL_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(recipes, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(PERSONAL_FILE)


def find_personal(name: str):
    """
    Returns the personal recipe with the given name, or None.
    """
    return next((r for r in load_personal() if r["name"] == name), None)


def parse_recipe(data) -> dict:
    """
    Validates a recipe received from a client and returns it in our recipe format.
    Aborts with 400 BAD REQUEST if the data is invalid.
    """
    if not isinstance(data, dict):
        abort(400, description="The request body must be a JSON object.")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or "/" in name:
        abort(400, description="'name' must be a non-empty string without '/'.")

    ingredients = data.get("ingredients", {})
    if not isinstance(ingredients, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in ingredients.items()):
        abort(400, description="'ingredients' must be an object of ingredient: measure strings.")

    recipe = dict(name=name.strip(), ingredients=ingredients)
    for field in ("image", "video", "instructions"):
        value = data.get(field) or ""
        if not isinstance(value, str):
            abort(400, description=f"'{field}' must be a string.")
        recipe[field] = value
    return recipe


@app.route("/personal", methods=["POST"])
def add_personal():
    """
    Saves a recipe sent as JSON to the personal list, then redirects to its page.
    A recipe with the same name is replaced.
    """
    recipe = parse_recipe(request.get_json(silent=True))
    recipes = [r for r in load_personal() if r["name"] != recipe["name"]]
    recipes.append(recipe)
    save_personal(recipes)
    # 303 tells the client to follow the redirect with a GET request
    return redirect(url_for("personal_recipe", name=recipe["name"], json=0), code=303)


@app.route("/personal/<name>/<int:json>", methods=["GET"])
def personal_recipe(name, json):
    """
    Returns a personal recipe as an HTML page (json == 0) or as JSON (json == 1).
    """
    if json not in (0, 1):
        abort(404, description="The flag must be 0 (page) or 1 (JSON).")
    recipe = find_personal(name)
    if recipe is None:
        abort(404, description=f"No personal recipe named {name!r}.")
    if json == 1:
        return jsonify(recipe)
    return render_template("recipe.html", ingredient=None, recipe=recipe)


@app.route("/personal/<name>", methods=["DELETE"])
def delete_personal(name):
    """
    Deletes the personal recipe with the given name.
    """
    recipes = load_personal()
    remaining = [r for r in recipes if r["name"] != name]
    if len(remaining) == len(recipes):
        abort(404, description=f"No personal recipe named {name!r}.")
    save_personal(remaining)
    return "", 204  # 204 NO CONTENT: success, nothing to return


@app.route("/personal/all", methods=["GET"])
def all_personal():
    """
    Returns all personal recipes as a JSON list.
    """
    return jsonify(load_personal())


if __name__ == '__main__':
    app.run(debug=True)
