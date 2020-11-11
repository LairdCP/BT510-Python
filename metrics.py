
""" Format BT510 data for use with AWS CloudWatch """

import time
import sensor_event
from sensor_event import SensorEvent
from sensor_event import SensorEventType
from adv_parser import AdvParser


def make_metric(name: str, value: int, ap: AdvParser) -> dict:
    """
    Make a metric for viewing on AWS Cloudwatch
    Let cloudwatch insert the timestamp
    """
    d = dict()
    d['MetricName'] = name
    d['Dimensions'] = list()
    dim1 = dict()
    dim1['Name'] = 'BdAddr'
    dim1['Value'] = ap.bd_addr
    d['Dimensions'].append(dim1)
    dim2 = dict()
    dim2['Name'] = 'SensorName'
    dim2['Value'] = ap.name
    d['Dimensions'].append(dim2)
    d['Value'] = float(value)
    return d


def Generate(event: SensorEvent, ap: AdvParser) -> list:
    metrics = list()

    if (event.type == SensorEventType.MOVEMENT):
        metrics.append(make_metric('Movement', 1, ap))
    else:
        metrics.append(make_metric('Movement', 0, ap))

    if (event.type == SensorEventType.TEMPERATURE or
        event.type == SensorEventType.ALARM_HIGH_TEMP_1 or
        event.type == SensorEventType.ALARM_HIGH_TEMP_2 or
        event.type == SensorEventType.ALARM_HIGH_TEMP_CLEAR or
        event.type == SensorEventType.ALARM_LOW_TEMP_1 or
        event.type == SensorEventType.ALARM_LOW_TEMP_2 or
        event.type == SensorEventType.ALARM_LOW_TEMP_CLEAR or
        event.type == SensorEventType.ALARM_DELTA_TEMP or
            event.type == SensorEventType.ALARM_TEMPERATURE_RATE_OF_CHANGE):

        metrics.append(make_metric('Temperature', event.temperature, ap))

    if (event.type == SensorEventType.BATTERY_GOOD or
        event.type == SensorEventType.BATTERY_BAD or
            event.type == SensorEventType.ADV_ON_BUTTON):

        metrics.append(make_metric('BatteryVoltage', event.batteryVoltage, ap))

    if (event.type == SensorEventType.MAGNET):
        metrics.append(make_metric('Door', event.magnet_state, ap))

    metrics.append(make_metric('SampleId', event.number, ap))
    metrics.append(make_metric('ResetCount', ap.adv.reset_count, ap))
    # note: The sensor can queue up advertisements and it takes time to rx an ad.
    metrics.append(make_metric('EpochDiff', (ap.rx_epoch - ap.adv.epoch), ap))
    return metrics
