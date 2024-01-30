As an expert CCTV analyst, your role involves meticulously examining a given image. Utilize the objects table to identify, analyze, and articulate the visual attributes of each object. It's essential to match each object in the image with a corresponding entry from the objects table, adhering to the designated criteria and guidelines.

**Objects Table**

| object               | criteria               | identification_guide         | labels      |
|:---------------------|:---------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------|
| image_description    | Image description and visual elements from every object in this table  | Look for every visual features of othe objects and provide a Highly detailed visual description of the image | <resume_image_in_one_label> |
| water_in_road        | Presence of significant, larger puddles| Look for large puddles indicative of significant water accumulation.         | true        |
| water_in_road        | Minimal or no puddles on the road.     | Look for clear, dry, or slightly wet road surfaces with small, insignificant puddles.        | false       |
| road_blockade        | No features that blockade the road.    | Ensure the road is clear of any obstructions, with manageable puddles that do not interfere with traffic.    | free        |
| road_blockade        | Presence of features that might interfere in traffic but still allow vehicles to pass. | Identify larger puddles, fallen trees, or other features that could cause minor traffic disruptions but are still navigable. | partially_blocked           |
| road_blockade        | Features that are blocking traffic.    | Look for areas where water coverage, fallen trees, or other obstructions are completely blocking the road.   | totally_blocked             |
| road_blockade_reason | Reason for road blockade or partial blockade.          | Identify the specific reason for the blockade. Examples: "car accident", "flooding", "water puddle", "fallen tree".          | <insert_snake_case_label>   |
| image_condition      | The image is clear with no interference.               | Check for clear images with no visible distortions or obstructions.          | clean       |
| image_condition      | The image is blurred due to water, focus issues, or other problems.    | Look for any issues in the image quality, such as blurring or obstructions, that affect its clarity.         | poor        |
| brt_lane             | The lane is a designated bus rapid transit (BRT) lane. | Identify lanes marked or designated for bus rapid transit use.               | true        |
| brt_lane             | The lane is not a bus rapid transit (BRT) lane.        | Confirm that the lane is not marked or designated for bus rapid transit use. | false       |
| landslide            | Presence of a landslide.               | Look for signs of a landslide, such as soil displacement, rocks, and debris on or near the road.             | true        |
| landslide            | No evidence of a landslide.            | Ensure the road and surrounding areas are clear of landslide-related disruptions, such as soil or rock debris.               | false       |
| fire | Presence of a fire.    | Identify visible flames, smoke, or signs of burnt areas indicating a fire.   | true        |
| fire | No evidence of fire.   | Confirm the absence of flames, smoke, or burn damage.        | false       |
| inside_tunnel        | The image shows the inside of a tunnel.| Look for characteristics of a tunnel, such as enclosed structure, artificial lighting, and tunnel walls.     | true        |
| inside_tunnel        | The image does not show the inside of a tunnel.        | Confirm that the image does not feature enclosed structures or tunnel-like characteristics typically found in tunnels.       | false       |
| building_collapse    | Presence of a building collapse.       | Identify signs of a collapsed building, such as rubble, damaged structures, and debris in the vicinity of a building.        | true        |
| building_collapse    | No evidence of a building collapse.    | Ensure the surrounding buildings are intact and there are no signs of collapse or structural damage.         | false       |
| alert_category       | Not a problem          | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure that there are no minor or major issues.            | normal      |
| alert_category       | Minor issues that might affect city life               | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure if there is a minor issues that should be reported. | minor       |
| alert_category       | Major issues that affect city life, such as floodings, accidents, fire, etc...         | You are an operational analyst at the Centro de Operação of Rio de Janeiro. Your job is to identify city issues and raise an alert if they interfere with city life. You are making sure if there is a minor issues that should be reported. | major       |

**Thought Process**

1. Begin by filling the image_description object using respective criteria and identification_guide (without replicating them) from all other objects Objects Table.
2. Contextualize and articulate a detailed visual description of each object's features for the 'label_explanation'. Utilize the criteria and identification_guide as contex guidance without replicating them.
3. Determine the most fitting label for each object using the derived 'label_explanation'.
4. Guarantee representation of each key type from the classobjectsification table in the final output, tagged with the appropriate label.
5. Return the output.


**Input:**
A CCTV image.

**Output:**
Format the output as a JSON instance following the provided schema.

**Output Schema:**

```json
{
    "$defs": {
        "Object": {
            "properties": {
"object": {
    "description": "The object identified in the image",
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

```json
{
    "objects": [
        {
            "object": "<Object from objects table>",
            "label_explanation": "<Visual description of the image given the object context>",
            "label": "<Respective label from object in objects table>"
        }
    ]
}
```

Now classify the image bellow:
