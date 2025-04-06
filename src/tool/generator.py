import tomllib
import json
from pathlib import Path

from data_classes import *

CWD = Path.cwd()
DATA_PATH_PATH = CWD / "src/main/data"
NAMESPACE = "mangocompatdelight"


def getId(path: str) -> str:
    return ID.of(NAMESPACE, path)


# Load the config file
INPUT_DATA_PATH = CWD / "src/tool/data.toml"
if not INPUT_DATA_PATH.exists():
    raise FileNotFoundError(f"Config file not found at {INPUT_DATA_PATH}")
with INPUT_DATA_PATH.open("rb") as data_file:
    raw_data = tomllib.load(data_file)
    data = AttributeDict.from_dict(raw_data)

# print(json.dumps(raw_data, indent="\t"))

# exit()


def log_factory():
    tree_bark_item = Item("farmersdelight:tree_bark")
    for suffix, strips in data.recipe.strip.items():
        for log in strips:
            input = Item(ID.of(log).withSuffix("log"))
            output = Item(ID.of(log).withSuffix(suffix))
            Recipes.FarmersDelight.axe_strip(
                [output, tree_bark_item, input]
            ).id(getId(input.id.id.replace(":", "/")))


log_factory()


def generate_recipes():
    # Write the recipes to the recipe path
    for recipe in recipes_list:
        namespace, path = recipe._id.split(":")
        recipe_path = get_path(DATA_PATH_PATH / namespace / "recipe" / f"{path}.json")
        with open(recipe_path, "w") as file:
            json.dump(recipe.json, file, indent=2)


generate_recipes()
