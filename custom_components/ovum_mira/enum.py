from enum import StrEnum


class Component(StrEnum):
    SYSTEM = "hsm"
    HEAT_PUMP = "heat_pump"
    HEATING_1 = "heating1"
    HEATING_2 = "heating2"
    HEATING_3 = "heating3"
    HEATING_4 = "heating4"
    HOT_WATER = "hot_water"
    BUFFER = "buffer"
    EMS = "ems"
