**Role:**

You are tasked with analyzing a CCTV image of Rio de Janeiro to identify potential city issues. Your analysis should focus on several key elements defined in an 'Objects Table', which includes criteria and identification guides for various objects and conditions that may impact city life. The goal is to classify these elements and provide a clear, concise description for each, enabling human CCTV operators to quickly understand and act upon the information. All objects from the 'Objects Table' MUST HAVE one entry in the output.


**Objects Table**

| object               | criteria                   | identification_guide                 | labels |
|:---------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------|
| image_description    | Image description and visual elements from the image               | Look for key features in the image and describe with at least 50 words. Resume de image in one word to fill the label.                   | [insert_image_description_snake_case_label]    |
| road_blockade        | No features that blockade the road.            | Ensure the road is clear of any obstructions, with manageable puddles that do not interfere with traffic.            | free   |
| road_blockade        | Presence of features that might interfere in traffic but still allow vehicles to pass. | Identify larger puddles, fallen trees, or other features that could cause minor traffic disruptions but are still navigable.             | partially_blocked          |
| road_blockade        | Features that are blocking traffic.            | Look for areas where water coverage, fallen trees, or other obstructions are completely blocking the road.           | totally_blocked            |
| road_blockade_reason | Reason for road blockade or partial blockade.  | Identify the specific reason for the blockade. Examples: "car_accident", "flooding", "water_puddle", "fallen_tree", "no_blockade"        | [insert_road_blockade_reason_snake_case_label] |
| water_in_road        | Presence of significant, larger puddles        | Look for large puddles indicative of significant water accumulation.         | true   |
| water_in_road        | Minimal or no puddles on the road.             | Look for clear, dry, or slightly wet road surfaces with small, insignificant puddles.            | false  |
| traffic_ease_vehicle | Minimal or no water on the road.               | Look for clear, dry, or slightly wet road surfaces and small, manageable puddles that do not interfere with traffic  | easy   |
| traffic_ease_vehicle | Presence of significant, larger puddles        | Detect larger puddles that could cause minor traffic disruptions but are still navigable for most vehicles.          | moderate                   |
| traffic_ease_vehicle | A partial portion of the road is covered with medium water level   | Identify areas where water coverage is extensive and high, causing notable hindrance to vehicle. | difficult                  |
| traffic_ease_vehicle | Complete submergence of the road with high water level             | Identify a scenarios where the road is entirely submerged/flooded, making it completely impassable for vehicles.     | impossibe                  |
| image_condition      | The image is clear with no interference.       | Check for clear images with no visible distortions or obstructions.          | clean  |
| image_condition      | The image is blurred due to water, focus issues, or other problems.| Look for any issues in the image quality, such as blurring or obstructions, that affect its clarity.                 | poor   |
| brt_lane             | The lane is a designated bus rapid transit (BRT) lane.             | Identify lanes marked or designated for bus rapid transit use.               | true   |
| brt_lane             | The lane is not a bus rapid transit (BRT) lane.| Confirm that the lane is not marked or designated for bus rapid transit use. | false  |
| landslide            | Presence of a landslide.   | Look for signs of a landslide, such as soil displacement, rocks, and debris on or near the road. | true   |
| landslide            | No evidence of a landslide.| Ensure the road and surrounding areas are clear of landslide-related disruptions, such as soil or rock debris.       | false  |
| fire                 | Presence of a fire.        | Identify visible flames, smoke, or signs of burnt areas indicating a fire.   | true   |
| fire                 | No evidence of fire.       | Confirm the absence of flames, smoke, or burn damage.    | false  |
| inside_tunnel        | The image shows the inside of a tunnel.        | Look for characteristics of a tunnel, such as enclosed structure, artificial lighting, and tunnel walls.             | true   |
| inside_tunnel        | The image does not show the inside of a tunnel.| Confirm that the image does not feature enclosed structures or tunnel-like characteristics typically found in tunnels.                   | false  |
| building_collapse    | Presence of a building collapse.               | Identify signs of a collapsed building, such as rubble, damaged structures, and debris in the vicinity of a building.| true   |
| building_collapse    | No evidence of a building collapse.            | Ensure the surrounding buildings are intact and there are no signs of collapse or structural damage.                 | false  |
| alert_category       | Not a problem              | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure that there are no minor or major issues.            | normal |
| alert_category       | Minor issues that might affect city life       | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure if there is a minor issues that should be reported. | minor  |
| alert_category       | Major issues that affect city life, such as floodings, accidents, fire, etc...         | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure if there is a minor issues that should be reported. | major  |

**Thought Process**

    1. Use the criteria and identification_guide as context to describe the visual features of each object and fill the label_explanation output. Do not simply repeat the criteria or identification_guide but use then as context for your description.
    2. Based on your visual description and analysis, select the most accurate label for each object from the options provided in the 'Objects Table'. You must use only the provided  labels!
    3. Ensure that EVERY OBJECT from the objects table HAS ONE ENTRY in the output with the respective label and detailed description.
    4. Return the output.


**Input:**
A CCTV image.

**Output:**

    - Format the output as a JSON instance following the provided schema.

**Output Schema:**


```json
{
    "$defs": {
        "Object": {
            "properties": {
                "object": {
"description": "The object from the  objects table",
"title": "Object",
"type": "string"
                },
                "label_explanation": {
"description": "Highly detailed visual description of the image given the object context",
"title": "Label Explanation",
"type": "string"
                },
                "label": {
"anyOf": [
    {
        "type": "boolean"
    },
    {
        "type": "string"
    }
],
"description": "Label indicating the condition or characteristic of the object",
"title": "Label"
                }
            },
            "required": [
                "object",
                "label_explanation",
                "label"
            ],
            "title": "Object",
            "type": "object"
        }
    },
    "properties": {
        "objects": {
            "items": {
                "$ref": "#/$defs/Object"
            },
            "title": "Objects",
            "type": "array"
        }
    },
    "required": [
        "objects"
    ],
    "title": "Output",
    "type": "object"
}
```


**Example Output:**

    - For each object analyzed, your output should resemble the following format:


```json
{
    "objects": [
        {
            "object": "<Object from objects table>",
            "label_explanation": "<Visual description of the image given the object context>",
            "label": "<Selected label from objects table>"
        }
    ]
}
```

Now classify the image bellow: