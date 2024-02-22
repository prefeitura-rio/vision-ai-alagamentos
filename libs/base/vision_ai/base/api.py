# -*- coding: utf-8 -*-
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from typing import Dict, List, Tuple

import requests


class VisionaiAPI:
    def __init__(self, username: str, password: str) -> None:
        self.BASE_URL = "https://vision-ai-api-staging-ahcsotxvgq-uc.a.run.app"
        self.username = username
        self.password = password
        self.headers, self.token_renewal_time = self._get_headers()

    def _get_headers(self) -> Tuple[Dict[str, str], float]:
        access_token_response = requests.post(
            f"{self.BASE_URL}/auth/token",
            data={"username": self.username, "password": self.password},
        )

        if access_token_response.status_code == 200:
            token = access_token_response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}, time.time()
        else:
            print(
                f"Status code: {access_token_response.status_code}\nResponse:{access_token_response.content}"
            )
            raise Exception()

    def _refresh_token_if_needed(self) -> None:
        if time.time() - self.token_renewal_time >= 60 * 50:
            self.headers, self.token_renewal_time = self._get_headers()

    def _get(self, path: str, timeout: int = 120) -> Dict:
        self._refresh_token_if_needed()
        try:
            response = requests.get(
                f"{self.BASE_URL}{path}", headers=self.headers, timeout=timeout
            )

            response.raise_for_status()
            return response.json()
        except requests.exceptions.ReadTimeout as _:  # noqa
            return {"items": []}

    def _put(self, path, json_data=None):
        self._refresh_token_if_needed()
        response = requests.put(
            f"{self.BASE_URL}{path}", headers=self.headers, json=json_data
        )
        return response

    def _post(self, path, json_data=None):
        self._refresh_token_if_needed()
        response = requests.post(
            f"{self.BASE_URL}{path}", headers=self.headers, json=json_data
        )
        return response

    def _delete(self, path: str, json_data: dict = None) -> Dict:
        self._refresh_token_if_needed()
        response = requests.delete(
            f"{self.BASE_URL}{path}", headers=self.headers, json=json_data
        )
        return response

    def _get_all_pages(self, path, page_size=100, timeout=120):

        # Function to get a single page
        def get_page(page, total_pages):
            # time each execution

            start = time.time()
            response = self._get(path=page, timeout=timeout)
            print(
                f"Page {page} out {total_pages} took {round(time.time() - start,2)} seconds"
            )
            return response

        if isinstance(path, str):

            print(f"Getting all pages for {path}")
            # Initial request to determine the number of pages
            initial_response = self._get(
                path=f"{path}?page=1&size=1", timeout=timeout
            )  # noqa
            if not initial_response:
                return []

            # Assuming the initial response contains the total number of items or pages # noqa
            total_pages = self._calculate_total_pages(initial_response, page_size)
            pages = [
                f"{path}?page={page}&size={page_size}"
                for page in range(1, total_pages + 1)  # noqa
            ]

        elif isinstance(path, list):
            total_pages = len(path)
            pages = path

        data = []
        with ThreadPoolExecutor(max_workers=total_pages) as executor:
            # Create a future for each page
            futures = [
                executor.submit(get_page, page, total_pages) for page in pages
            ]  # noqa

            for future in as_completed(futures):
                response = future.result()
                items = response.get("items", response)
                if isinstance(items, list):
                    data.extend(items)
                elif isinstance(items, dict):
                    data.append(items)

        print("Getting all pages done!!!")
        return data

    def _calculate_total_pages(self, response, page_size):
        return round(response["total"] / page_size) + 1

    def get_item_from_slug(self, slug, data):
        return next((item for item in data if item["slug"] == slug), None)

    def process_items(
        self,
        items: List[Dict],
        objects: List[Dict] = None,
        cameras: List[Dict] = None,
        prompts: List[Dict] = None,
    ) -> None:
        """
        Processes a list of items, potentially involving object creation, label
        association, and interaction with cameras and prompts. Optimizes API calls
        by allowing pre-fetched object, camera, and prompt data to be provided.

        Args:

            items (List[Dict]): A list of dictionaries, each containing the following keys:
                * 'camera_id' (str, Optional): The ID of the camera to add the object.
                * 'object_slug': The slug of the object to add associations.
                * 'label_slug' (str, Optional): The slug of the label to put/post in the object.
                * 'criteria' (str, Optional): The criteria to put/post in the label.
                * 'identification_guide' (str, Optional): The identification guide to put/post in the label.
                * 'prompt_id' (str, Optional): The ID of the prompt to add the object.

            objects (List[Dict], Optional): A list of pre-fetched object dictionaries. If not provided,
                    will make one API call per item.

            cameras (List[Dict], Optional): A list of pre-fetched camera dictionaries. If not provided,
                    will make one API call per item.

            prompts (List[Dict], Optional): A list of pre-fetched prompt dictionaries. If not provided,
                    will make one API call per item.

        Example:

        ```python

        from vision_ai_api import APIVisionAI

        vision_ai_api = APIVisionAI(
            username="username",
            password="password",
        )

        objects = vision_ai_api._get_all_pages("/objects")
        cameras = vision_ai_api._get_all_pages("/cameras", page_size=3000)
        prompts = vision_ai_api._get_all_pages("/prompts")

        items_to_process = [
            {
                "object_slug": "str",
                "label_slug": "str",
                "criteria": str,
                "identification_guide": str,
                "camera_id": "str",
                "prompt_id": "str"
            },
        ]

        vision_ai_api.process_items(
            items=items_to_process,
            objects=objects,
            cameras=cameras,
            prompts=prompts
        )
        ```
        """
        if objects is None:
            objects = self._get("/objects").get("items", [])

        def process_single(item, index, total):
            start_time = time.time()
            try:
                self._process_single_item(item, objects, cameras, prompts)
                end_time = time.time()
                print(
                    f"Processed item {index + 1}/{total} in {end_time - start_time:.2f} seconds.\n\n"
                )
            except Exception as e:
                print(f"Error processing item {index + 1}/{total}: {e}")
                raise e

        total_items = len(items)
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_single, item, index, total_items)
                for index, item in enumerate(items)
            ]
            wait(futures)

    def _process_single_item(
        self, item: Dict, objects: list, cameras: list = None, prompts: list = None
    ) -> None:
        camera_id = item.get("camera_id")
        object_slug = item["object_slug"]
        label_slug = item.get("label_slug")
        criteria = item.get("criteria")
        identification_guide = item.get("identification_guide")
        prompt_id = item.get("prompt_id")
        object_data = next(
            (obj for obj in objects if obj.get("slug") == object_slug), None
        )
        # Ensure object exists
        object_id = self._ensure_object_exists(
            object_slug=object_slug, object_data=object_data
        )

        # Ensure label exists or create it

        if (
            (criteria is not None)
            and (identification_guide is not None)
            and (label_slug is not None)
        ):
            self._ensure_label_exists(
                object_id=object_id,
                object_slug=object_slug,
                label_slug=label_slug,
                criteria=criteria,
                identification_guide=identification_guide,
                labels=object_data.get("labels", []),
            )

        # Associate object with camera
        if camera_id:
            self._associate_object_with_camera(
                object_id=object_id,
                object_slug=object_slug,
                camera_id=camera_id,
                cameras=cameras,
            )

        # Associate object with prompt
        if prompt_id:
            self._associate_object_with_prompt(
                object_id=object_id,
                object_slug=object_slug,
                prompt_id=prompt_id,
                prompts=prompts,
            )

    def _ensure_object_exists(self, object_slug: str, object_data: list) -> str:
        if object_data:
            print(f"Object '{object_slug}' already exists. Local Test!")
            return object_data["id"]  # Return existing object ID

        print(f"Creating object '{object_slug}'...")
        response = self._post(
            "/objects", json_data={"name": object_slug, "slug": object_slug}
        )
        if response.status_code == 200:
            print(f"Object '{object_slug}' created successfully.")
            return response.json().get("id")  # Return new object ID
        else:
            print(f"Failed to create object '{object_slug}'. Error: {response.json()}")
            raise Exception(response.json())

    def _ensure_label_exists(
        self,
        object_id: str,
        object_slug: str,
        label_slug: str,
        criteria: str,
        identification_guide: str,
        labels: list,
    ) -> None:
        label_data = next(
            (lbl for lbl in labels if lbl.get("value") == label_slug), None
        )
        if label_data:
            print(f"Label '{label_slug}' exists. Updating label...")
            response = self._put(
                f'/objects/{object_id}/labels/{label_data["id"]}',
                json_data={"criteria": criteria, "guide": identification_guide},
            )
            if response.status_code == 200:
                print(f"Label '{label_slug}' updated successfully.")
            else:
                print(
                    f"Failed to update label '{label_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"
                )
                raise Exception("Failed to update label")
        else:
            print(f"Label '{label_slug}' does not exist. Creating label...")
            label_data = {
                "value": label_slug,
                "criteria": criteria,
                "identification_guide": identification_guide,
            }
            response = self._post(f"/objects/{object_id}/labels", json_data=label_data)
            if response.status_code == 200:
                print(f"Label '{label_slug}' created successfully.")
            elif response.status_code == 409:
                print(
                    f"Label '{label_slug}' already exists for object  {label_slug}.\nStatus Code: {response.status_code}\nError: {response.json()}"
                )

            elif response.status_code == 422:
                print(
                    f"Label '{label_slug}': Validation error when associating object'{object_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"  # noqa
                )
                raise Exception()

            else:
                print(
                    f"Failed to create label '{label_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"
                )
                raise Exception()

    def _associate_object_with_camera(
        self, object_id: str, object_slug: str, camera_id: str, cameras: list = None
    ) -> None:

        # Prepare the endpoint path
        if cameras is not None:
            camera_data = next(
                (cam for cam in cameras if cam.get("id") == camera_id), None
            )
            if object_slug in camera_data.get("objects", []):
                print(
                    f"Camera {camera_id}: Object '{object_slug}' is already associated. Local Test!"
                )
                return

        path = f"/objects/{object_id}/cameras/{camera_id}"
        # Prepare the query parameters
        # params = {"object_id": object_id}
        # Make the POST request with the required parameters
        response = requests.post(f"{self.BASE_URL}{path}", headers=self.headers)
        # Check the response status and handle accordingly
        if response.status_code == 200:
            print(
                f"Camera {camera_id}: Object '{object_slug}' associated successfully."
            )
        elif response.status_code == 409:
            print(f"Camera {camera_id}: Object' {object_slug}' is already associated.")
        elif response.status_code == 422:
            print(
                f"Camera {camera_id}: Validation error when associating object' {object_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"  # noqa
            )
            raise Exception()
        else:
            print(
                f"Camera {camera_id}: Failed to associate object '{object_slug}'.\nStatus Code: {response.status_code} \nError: {response.json()}"
            )
            raise Exception()

    def _associate_object_with_prompt(
        self, object_id: str, object_slug: str, prompt_id: str, prompts: list = None
    ) -> None:

        if prompts is not None:
            prompt_data = next(
                (prompt for prompt in prompts if prompt.get("id") == prompt_id), None
            )

            if object_slug in prompt_data.get("objects", []):
                print(
                    f"Prompt: Object '{object_slug}' is already associated. Local Test!"
                )
                return

        response = self._post(f"/prompts/{prompt_id}/objects?object_id={object_id}")

        if response.status_code == 200:
            print(f"Prompt: Object'{object_slug}'associated successfully.")
        elif response.status_code == 409:
            print(f"Prompt: Object'{object_slug}'is already associated.")
        elif response.status_code == 422:
            print(
                f"Prompt: Validation error when associating object '{object_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"
            )
            raise Exception()
        else:
            print(
                f"Prompt: Failed to associate object '{object_slug}'.\nStatus Code: {response.status_code}\nError: {response.json()}"
            )
            raise Exception()

    def process_remove_items(
        self,
        items: List[Dict],
        objects: List[Dict] = None,
        cameras: List[Dict] = None,
        prompts: List[Dict] = None,
    ) -> None:
        """
        Processes a list of items to remove associations with objects, cameras, and prompts.
        This involves deleting labels from objects, removing objects from cameras,
        and disassociating objects from prompts.

        Args:
            items (List[Dict]): A list of dictionaries, each containing the following keys:
                * 'camera_id' (str, Optional): The ID of the camera to remove the object from.
                * 'object_slug': The slug of the object to remove associations.
                * 'label_slug' (str, Optional): The slug of the label to remove from the object.
                * 'prompt_id' (str, Optional): The ID of the prompt to remove the object from.
            objects: (List[Dict], optional) Pre-fetched objects data. If not provided,
                    will be fetched from the API.
            cameras: (List[Dict], Optional) Pre-fetched cameras data. If not provided,
                    will make one API call per item.
            prompts: (List[Dict], Optional) Pre-fetched prompts data. If not provided,
                    will make one API call per item.

        Example:

        ```python

        from vision_ai_api import APIVisionAI

        vision_ai_api = APIVisionAI(
            username="username",
            password="password",
        )

        objects = vision_ai_api._get_all_pages("/objects")
        cameras = vision_ai_api._get_all_pages("/cameras", page_size=3000)
        prompts = vision_ai_api._get_all_pages("/prompts")

        items_to_remove = [
            {
                "camera_id": "str",
                'object_slug': 'str',
                'label_slug': 'str',
                "prompt_id": "str"
            }
        ]

        r = vision_ai_api.process_remove_items(
            items=items_to_remove,
            objects=objects,
            cameras=cameras,
            prompts=prompts
        )

        ```

        """
        # Fetch data if not provided
        if objects is None:
            objects = self._get("/objects").get("items", [])

        # Function to process a single item
        def process_single_remove(item, index, total):
            start_time = time.time()
            try:
                self._process_single_item_remove(item, objects, cameras, prompts)
                end_time = time.time()
                print(
                    f"Processed item {index + 1}/{total} in {end_time - start_time:.2f} seconds.\n\n"
                )
            except Exception as e:
                print(f"Error processing item {index + 1}/{total}: {e}")
                raise e

        total_items = len(items)
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_single_remove, item, index, total_items)
                for index, item in enumerate(items)
            ]
            wait(futures)

    def _process_single_item_remove(
        self, item: Dict, objects: list, cameras: list = None, prompts: list = None
    ):

        camera_id = item.get("camera_id")
        object_slug = item["object_slug"]
        label_slug = item.get("label_slug")
        prompt_id = item.get("prompt_id")
        # Ensure object exists
        object_data = next(
            (obj for obj in objects if obj.get("slug") == object_slug), None
        )
        if not object_data:
            print(f"Object '{object_slug}' not found, skipping deletions. Local Test!")
            return
        object_id = object_data["id"]

        # Delete label from object
        if label_slug:
            self._remove_label_from_object(
                object_id=object_id,
                object_slug=object_slug,
                label_slug=label_slug,
                labels=object_data.get("labels", []),
            )

        # Delete object from camera
        if camera_id:
            self._remove_object_from_camera(
                object_id=object_id,
                object_slug=object_slug,
                camera_id=camera_id,
                cameras=cameras,
            )

        # Delete object from prompt
        if prompt_id:
            self._remove_object_from_prompt(
                object_id=object_id,
                object_slug=object_slug,
                prompt_id=prompt_id,
                prompts=prompts,
            )

    # Method to delete a label from an object
    def _remove_label_from_object(
        self,
        object_id: str,
        object_slug: str,
        label_slug: str,
        labels=None,
    ) -> None:

        label_data = next(
            (lbl for lbl in labels if lbl.get("value") == label_slug), None
        )
        if not label_data:
            print(
                f"Label '{label_slug}' not found on object '{object_slug}' . Local Test!"
            )
            return

        path = f"/objects/{object_id}/labels/{label_slug}"
        response = self._delete(path)
        if response.status_code == 200:
            print(
                f"Label '{label_slug}': deleted from object '{object_slug}'  successfully."
            )
        else:
            print(
                f"Label '{label_slug}': falied to delete from object '{object_slug}' .\nStatus Code:{response.status_code}\nError: {response.json()}"
            )
            raise Exception()

    # Method to delete an object from a camera
    def _remove_object_from_camera(
        self, camera_id: str, object_slug: str, object_id: str, cameras=None
    ) -> None:
        if cameras is not None:
            camera_data = next(
                (cam for cam in cameras if cam.get("id") == camera_id), None
            )
            if object_slug not in camera_data.get("objects", []):
                print(
                    f"Camera {camera_id}: object '{object_slug}'  not found. Local Test!"
                )
                return
        path = f"/cameras/{camera_id}/objects/{object_id}"
        response = self._delete(path)
        if response.status_code == 200:
            print(
                f"Camera ID {camera_id}: object '{object_slug}'  deleted successfully."
            )
        else:
            print(
                f"Camera {camera_id}: failed to delete '{object_slug}' .\nStatus Code:{response.status_code}\nError: {response.json()}"
            )
            raise Exception()

    # Method to remove an object from a prompt
    def _remove_object_from_prompt(
        self, prompt_id: str, object_slug: str, object_id: str, prompts=None
    ) -> None:

        if prompts is not None:
            prompt_data = next(
                (prmt for prmt in prompts if prmt.get("id") == prompt_id), None
            )
            if object_slug not in prompt_data.get("objects", []):
                print(f"Prompt: object '{object_slug}'  not found. Local Test!")
                return

        path = f"/prompts/{prompt_id}/objects/{object_id}"
        response = self._delete(path)
        if response.status_code == 200:
            print(f"Prompt: object '{object_slug}'  removed successfully.")
        else:
            print(
                f"Prompt {prompt_id}: falied remove object '{object_slug}' .\nStatus Code:{response.status_code}\nError: {response.json()}"
            )
            raise Exception()
