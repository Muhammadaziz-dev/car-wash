# devices/services/configuration.py
def serialize_config(config, include_programs=False):
    data = {
        "price_per_minute": float(config.price_per_minute),
        "default_timeout": config.default_timeout,
        "bonus_duration_enabled": config.bonus_duration_enabled,
        "bonus_duration_amount": config.bonus_duration_amount,
        "valve_reset_timeout": config.valve_reset_timeout,
        "engine_performance": config.engine_performance,
        "pump_performance": config.pump_performance,
    }
    if include_programs:
        data["programs"] = [
            {
                "id": ps.program.id,
                "name": ps.program.name,
                "price_per_second": str(ps.program.price_per_second)
            }
            for ps in config.deviceprogramsetting_set.filter(is_enabled=True)
        ]
    return data
