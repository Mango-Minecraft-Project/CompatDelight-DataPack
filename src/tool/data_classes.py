import re
from typing import Self, Union, Any
from json import dumps
from pathlib import Path


countable_pattern = re.compile(r"^(\d+)x ((?:[a-z0-9-_.]+)?:[a-z0-9-_./]+)$")


def get_path(path: Path) -> Path:
    if not path.exists():
        # Check if the path is a file or directory
        if path.suffix == "":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
    return path


class AttributeDict:
    @classmethod
    def from_dict(cls, data: dict) -> "AttributeDict":
        cls = cls()
        for key, value in data.items():
            if isinstance(value, dict):
                value = cls.from_dict(value)
            setattr(cls, key, value)
        return cls

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        delattr(self, key)

    def items(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in dir(self) if not key.startswith("__")}


class Conditions(dict):
    always = {
        "type": "neoforge:always",
    }
    never = (
        {
            "type": "neoforge:never",
        },
    )

    @staticmethod
    def _not(value: "Conditions") -> "Conditions":
        return {
            "type": "neoforge:not",
            "value": value,
        }

    @staticmethod
    def _and(*values: "Conditions") -> "Conditions":
        return {
            "type": "neoforge:and",
            "values": [*values],
        }

    @staticmethod
    def _or(*values: "Conditions") -> "Conditions":
        return {
            "type": "neoforge:or",
            "values": [*values],
        }

    @staticmethod
    def mod_loaded(mod_id: str) -> "Conditions":
        return {
            "type": "neoforge:mod_loaded",
            "modid": mod_id,
        }

    @staticmethod
    def registered(registry: str, value: str) -> "Conditions":
        return {
            "type": "neoforge:registered",
            "registry": registry,
            "value": value,
        }

    @staticmethod
    def tag_empty(registry: str, tag: str) -> "Conditions":
        return {
            "type": "neoforge:tag_empty",
            "registry": registry,
            "tag": tag,
        }

    @staticmethod
    def feature_flag_enabled(*flag: str) -> "Conditions":
        return {
            "type": "neoforge:feature_flag_enabled",
            "flag": [*flag],
        }


class ID(str):
    id: str
    namespace: str
    path: str

    def __init__(self, id: str) -> None:
        self.id = id
        self.namespace, self.path = id.split(":")

    def __iter__(self):
        """Returns an iterator over the namespace and path of the ID."""
        return iter((self.namespace, self.path))

    def __str__(self) -> str:
        return self.id

    def copy(self) -> Self:
        new = self.__new__(self)
        new.__dict__ |= self.__dict__
        return new
    
    def withPrefix(self, prefix: str) -> Self:
        new = self.copy()
        namespace, path = new.id
        new.id = ID.of(f"{namespace}:{prefix}{path}")
        return new
    
    def withSuffix(self, suffix: str) -> Self:
        new = self.copy()
        namespace, path = new.id
        new.id = ID.of(f"{namespace}:{path}{suffix}")
        return new

    @staticmethod
    def of(id: Union[str, "ID"], path: str = None) -> "ID":
        if isinstance(id, ID):
            return id
        if path != None:
            id = f"{id}:{path}"
        if len(id.split(":")) == 1:
            id = "minecraft:" + id
        return ID(id)


class Item:
    id: ID
    count: int
    chance: float

    def __init__(self, id: ID | str, count: int = 1) -> None:
        countable_id = countable_pattern.match(id)
        if countable_id != None:
            id = countable_id.group(2)
            self.count = int(countable_id.group(1))
        else:
            self.count = count
        self.id = ID.of(id)
        self.chance = None

    def copy(self) -> Self:
        new = self.__new__(self)
        new.__dict__ |= self.__dict__
        return new
    
    def withId(self, id: Union[str, ID]) -> Self:
        new = self.copy()
        new.id = ID.of(id)
        return new

    def withChance(self, chance: float) -> Self:
        if chance < 0 or chance > 1:
            raise ValueError("Chance must be between 0 and 1")
        new = self.copy()
        new.chance = chance
        return new

    def to_ingredient_json(self) -> dict:
        return {"item": self.id, "count": self.count}

    def to_result_json(self) -> dict:
        json = {
            "item": {
                "id": self.id,
                "count": self.count,
            }
        }
        if self.chance != None:
            json["chance"] = self.chance
        return json


class ToolType:
    @staticmethod
    def item_ability(action: str) -> dict:
        return {"type": "farmersdelight:item_ability", "action": action}


class Sound:
    def __init__(self, sound_id: str) -> None:
        self.sound_id = sound_id

    def to_json(self) -> dict:
        return {"sound_id": self.sound_id}


class Recipe:
    json: dict
    _id: str

    def __init__(self, json: dict, id: Union[str, ID] = None):
        self.json = json
        if id == None:
            type = json["type"]
            namespace, path = type.split(":")
            id = f"{namespace}:{path}/{len(recipes_list)}"
        self._id = self.id(id)
        recipes_list.append(self)

    def id(self, id: Union[str, ID]) -> Self:
        self._id = ID.of(id).id
        return self

    def condition(self, condition: dict) -> Self:
        condition_key = "neoforge:conditions"
        if condition_key not in self.json:
            self.json[condition_key] = []
        self.json[condition_key].append(condition)
        return self

    def auto(self, mod_id: str) -> Self:
        return self.condition(Conditions.mod_loaded(mod_id))

    def __repr__(self) -> str:
        return dumps(self.json, indent="\t", separators=(",", ": "))


recipes_list: list[Recipe] = []


class Recipes:
    class FarmersDelight:
        @staticmethod
        def cutting(
            result: list[Item], ingredients: Item, tool: ToolType, sound: Sound = None
        ) -> Recipe:
            json = {
                "type": "farmersdelight:cutting",
                "ingredients": [ingredients.to_ingredient_json()],
                "result": [item.to_result_json() for item in result],
                "tool": tool,
            }
            if sound:
                json["sound"] = sound.to_json()
            return Recipe(json)

        @staticmethod
        def axe_strip(result: list[Item], ingredients: Item) -> Recipe:
            return Recipes.FarmersDelight.cutting(
                result,
                ingredients,
                ToolType.item_ability("axe_strip"),
                Sound("minecraft:item.axe.strip"),
            )

        @staticmethod
        def axe_dig(result: list[Item], ingredients: Item) -> Recipe:
            return Recipes.FarmersDelight.cutting(
                result,
                ingredients,
                ToolType.item_ability("axe_dig"),
                Sound("minecraft:item.axe.dig"),
            )
