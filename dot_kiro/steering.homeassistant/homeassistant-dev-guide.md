# Home Assistant Development Guide

## YAML Standards

You MUST follow [Home Assistant YAML Style Guide](https://developers.home-assistant.io/docs/documenting/yaml-style-guide/).

### New YAML Syntax

- You MUST use the new syntax
- Since Home Assistant 2024.8, the following YAML syntax changes were introduced

- `service:` → `action:`
  - e.g. `service: light.turn_on` → `action: light.turn_on`
- `trigger:` → `triggers:` (top-level pluralization)
- `condition:` → `conditions:` (top-level pluralization)
- `action:` → `actions:` (top-level pluralization)
- `platform:` → `trigger:`
  - inside `triggers:` block, e.g. `platform: state` → `trigger: state`
- `data: entity_id:` → `target: entity_id:`
  - use `target:` for `entity_id`, `device_id`, `area_id`; other options stay in `data:`

```yaml
# New syntax example
automation:
  triggers:
    - trigger: state
      entity_id: binary_sensor.motion
  conditions:
    - condition: state
      entity_id: sun.sun
      state: below_horizon
  actions:
    - action: light.turn_on
      target:
        entity_id: light.living_room
      data:
        brightness: 255
```

Reference:
- [Home Assistant 2024.8 Release Notes](https://www.home-assistant.io/blog/2024/08/07/release-20248/)
- [Home Assistant 2024.10 Release Notes](https://www.home-assistant.io/blog/2024/10/02/release-202410/)
