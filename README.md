# SmartThingsLights integration for HomeAssistant


### Installation

Copy this folder to `<config_dir>/custom_components/smartthingslights/`.

Add the following entry in your `configuration.yaml`:

```yaml
light:
  - platform: smartthingslights
    token: smartthings token
    exclude:
      - LEDBLE-0387D5
```