import json
import os
import random
import requests
from flask import Flask, render_template, jsonify, request, redirect, abort

app = Flask(__name__)

PERSONAL_RECIPES_FILE = "personal_recipes.json"


def load_personal_recipes() -> list:
    if not os.path.exists(PERSONAL_RECIPES_FILE):
        return []
    with open(PERSONAL_RECIPES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_personal_recipes(recipes: list) -> None:
    with open(PERSONAL_RECIPES_FILE, "w", encoding="utf-8") as f:
        json.dump(recipes, f, indent=4, ensure_ascii=False)


def get_recipe_for(main_ingredient: str) -> dict | None:
    """
    Fetch a random recipe with a specified main ingredient.
    The recipes are requested from "themealdb" API (and personal recipes).
    """
    # EXTRA BONUS: Check personal recipes list as well
    personal_matches = []
    for r in load_personal_recipes():
        # Match if main_ingredient appears in any of the recipe's ingredient keys
        if any(main_ingredient.lower() in ing.lower() for ing in r.get("ingredients", {})):
            personal_matches.append(r)

    # 1. Fetch list of recipes from TheMealDB
    filter_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={main_ingredient}"
    filter_resp = requests.get(filter_url).json()
    api_meals = filter_resp.get("meals") or []

    # Combine candidates (tagging source so we know how to fetch full details)
    candidates = [("personal", r) for r in personal_matches] + [("api", m) for m in api_meals]

    if not candidates:
        return None

    # 2. Choose a random recipe
    source, chosen = random.choice(candidates)
    if source == "personal":
        return chosen

    # 3. Fetch full recipe instructions by ID
    meal_id = chosen["idMeal"]
    lookup_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    lookup_resp = requests.get(lookup_url).json()
    meal_details = lookup_resp["meals"][0]

    # 4. Extract ingredients and measures (strIngredient1..20 and strMeasure1..20)
    ingredients = {}
    for i in range(1, 21):
        ing = meal_details.get(f"strIngredient{i}")
        measure = meal_details.get(f"strMeasure{i}")
        if ing and ing.strip():
            ingredients[ing.strip()] = measure.strip() if measure else ""

    return dict(
        name=meal_details.get("strMeal", ""),
        image=meal_details.get("strMealThumb", ""),
        video=meal_details.get("strYoutube", ""),
        instructions=meal_details.get("strInstructions", ""),
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
    Returns a JSON with the output of `get_recipe_for`.
    """
    recipe_data = get_recipe_for(ingredient)
    if recipe_data is None:
        abort(404)

    return jsonify(recipe_data)


# --- BONUS ENDPOINTS ---

@app.route('/personal', methods=['POST'])
def add_personal_recipe():
    new_recipe = request.get_json()
    if not new_recipe or "name" not in new_recipe:
        abort(400)

    recipes = load_personal_recipes()
    recipes.append(new_recipe)
    save_personal_recipes(recipes)

    return redirect(f"/personal/{new_recipe['name']}/0")


@app.route('/personal/<name>/<int:json_flag>', methods=['GET'])
def get_personal_recipe(name, json_flag):
    if json_flag not in (0, 1):
        abort(404)

    recipes = load_personal_recipes()
    found = next((r for r in recipes if r.get("name") == name), None)
    if found is None:
        abort(404)

    if json_flag == 1:
        return jsonify(found)

    return render_template("recipe.html", ingredient="", recipe=found)


@app.route('/personal/<name>', methods=['DELETE'])
def delete_personal_recipe(name):
    recipes = load_personal_recipes()
    updated = [r for r in recipes if r.get("name") != name]

    if len(updated) == len(recipes):
        abort(404)

    save_personal_recipes(updated)
    return jsonify({"status": "deleted", "name": name})


@app.route('/personal/all', methods=['GET'])
def get_all_personal_recipes():
    return jsonify(load_personal_recipes())


if __name__ == '__main__':
    app.run(debug=True)
