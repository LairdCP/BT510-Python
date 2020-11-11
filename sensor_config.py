
""" Import sensor configuration with type checking """

import json


class sensor_config:
    def __init__(self, fname="default_sensor_configuration.json"):
        with open(fname, 'r') as f:
            self.config = json.load(f)

    def ask_user_for_changes(self) -> None:
        for (attribute, value) in self.config.items():
            v = input(
                f'Enter new value for "{attribute}" ({value}) - Press enter to keep default\n>')
            if v != "":
                if isinstance(value, str):
                    try:
                        vtyped = str(v)
                        self.config[attribute] = vtyped
                    except:
                        print(f'Wrong type for string {attribute}')
                elif isinstance(value, int):
                    try:
                        vtyped = int(v)
                        self.config[attribute] = vtyped
                    except:
                        print(f'Wrong type for string {attribute}')
                elif isinstance(value, float):
                    try:
                        vtyped = float(v)
                        self.config[attribute] = vtyped
                    except:
                        print(f'Wrong type for string {attribute}')
                else:
                    print("Unsupported type")

    def get_kwargs(self):
        return dict(self.config)
