"use client";

import React, { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { Spinner } from "@/components/Spinner"; // You need to create this Spinner component

import ProtectRoute from "@/components/ProtectRoute";
import api from "@/utils/api";

type IdentificationIndexes = {
  [key: string]: number;
};

type Label = {
  criteria: string;
  id: string;
  identification_guide: string;
  value: string;
  text: string;
};

type ObjectItem = {
  explanation: string;
  id: string;
  labels: Label[];
  name: string;
  question: string;
  slug: string;
  title: string;
};

const ClassifyPage = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [images, setImages] = useState<any[]>([]);
  const [identificationIndexes, setIdentificationIndexes] =
    useState<IdentificationIndexes>({});
  const [objects, setObjects] = useState<ObjectItem[]>([]);
  const [objectsLabels, setObjectsLabels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [imageLoading, setImageLoading] = useState(true);
  const [options, setOptions] = useState<any[]>([{ text: "", value: "" }]);

  // Dummy data for title and subtitle
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");

  const normalizeData = (objects: ObjectItem[]) => {
    return objects
      .map((obj) =>
        obj.labels.map((label) => ({
          ...label,
          name: obj.name,
          object_id: obj.id,
        })),
      ) // Normalize and flatten labels with name and object_id
      .flat() // Flatten the array of arrays into a single array
      .filter(
        (label) => label.value !== "null" || label.name === "image_description",
      ) // Apply the mask filter
      .map(
        ({
          id,
          criteria,
          identification_guide,
          value,
          text,
          name,
          object_id,
        }) => ({
          // Select specific fields and rename them
          object: name,
          label_id: id,
          criteria,
          identification_guide,
          label: value,
          text,
          object_id,
        }),
      );
  };

  const sendUserIdentification = async (
    identificationId: string,
    label: string,
  ) => {
    await api.post("/identifications", {
      identification_id: identificationId,
      label,
    });
  };

  useEffect(() => {
    const loadImages = async () => {
      let allImages = await api.get_all_pages("/identifications/ai", 100);
      allImages = allImages.filter(
        (image) => image.object !== "image_description",
      );
      setImages(allImages);
      let identificationIndex = 0;
      let tmpIdentificationIndexes: IdentificationIndexes = {};
      allImages.forEach((image, index) => {
        if (!tmpIdentificationIndexes[image.snapshot.image_url]) {
          tmpIdentificationIndexes[image.snapshot.image_url] =
            identificationIndex;
          identificationIndex++;
        }
      });
      setIdentificationIndexes(tmpIdentificationIndexes);
      setLoading(false);
    };

    loadImages();
  }, []);

  useEffect(() => {
    const loadObjects = async () => {
      const objects = await api.get_all_pages("/objects", 100);
      setObjects(objects);
      const normalizedObjects = normalizeData(objects);
      setObjectsLabels(normalizedObjects);
    };

    loadObjects();
  }, []);

  useEffect(() => {
    if (images.length < 1) return;
    let currentImage = images[currentIndex];
    let currentObject = currentImage.object;
    let possibleLabels = objectsLabels.filter(
      (label) => label.object === currentObject,
    );
    console.log(possibleLabels);
    setOptions(possibleLabels);
    setTitle(currentImage.question);
    setSubtitle(currentImage.explanation);
    setCurrentImageIndex(
      identificationIndexes[currentImage.snapshot.image_url],
    );
  }, [currentIndex, images, objectsLabels, identificationIndexes]);

  const handleClassify = async (identificationId: string, label: string) => {
    console.log(`Classifying identification ${identificationId} as ${label}`);
    await sendUserIdentification(identificationId, label);
    const currentObject = images[currentIndex].object;
    // If the current object is "image_corrupted" and the label is "true",
    // send null label for all identifications before we reach the next image.
    let jump = 1;
    if (currentObject === "image_corrupted" && label === "true") {
      while (
        currentIndex + jump < images.length &&
        images[currentIndex + jump].snapshot.image_url ===
          images[currentIndex].snapshot.image_url
      ) {
        await sendUserIdentification(images[currentIndex + jump].id, "null");
        jump++;
      }
    }
    // Also, if the current object is "rain" and the label is "false",
    // send null for the next identification if the object is "water_level".
    else if (currentObject === "rain" && label === "false") {
      if (
        currentIndex + jump < images.length &&
        images[currentIndex + jump].snapshot.image_url ===
          images[currentIndex].snapshot.image_url &&
        images[currentIndex + 1].object === "water_level"
      ) {
        await sendUserIdentification(images[currentIndex + 1].id, "null");
        jump++;
      }
    }
    if (currentIndex + jump < images.length) {
      if (
        images[currentIndex + jump].snapshot.image_url !==
        images[currentIndex].snapshot.image_url
      ) {
        setImageLoading(true);
      }
      setCurrentIndex(currentIndex + jump);
    }
  };

  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      // Check if event.key is a number
      if (isNaN(parseInt(event.key))) return;
      const keyIndex = parseInt(event.key) - 1;
      if (keyIndex < 0 || keyIndex > options.length - 1) return;
      const label = options[keyIndex].label;
      handleClassify(images[currentIndex].id, label);
    },
    [currentIndex, images, options],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [handleKeyPress]);

  if (loading) {
    return <Spinner />;
  }

  const imageToClassify = images[currentIndex];

  return (
    <div className="flex flex-row h-screen">
      <div className="flex flex-col w-3/5">
        <h1 className="text-xl font-bold p-4"></h1>
        <p className="text-center">{`Imagem: ${currentImageIndex} de ${
          Object.keys(identificationIndexes).length
        }`}</p>
        <div className="relative w-full h-3/4">
          {imageLoading && <Spinner />}{" "}
          {/* Show spinner while image is loading */}
          <Image
            src={imageToClassify.snapshot.image_url}
            alt="Classification subject"
            layout="fill"
            objectFit="contain"
            onLoadingComplete={() => setImageLoading(false)} // Set image as loaded
          />
        </div>
      </div>
      <div className="flex flex-col w-2/5 p-4">
        <div className="mb-4">
          <p className="text-lg font-semibold">{title}</p>
          <p className="text-md">{subtitle}</p>
        </div>
        <div className="flex flex-col">
          {options.map((option, index) => (
            <button
              key={option.label}
              className="px-4 py-2 bg-blue-500 text-white rounded shadow mb-2"
              onClick={() => handleClassify(imageToClassify.id, option.label)}
              disabled={imageLoading} // Disable button while image is loading
            >
              {`${index + 1}. ${option.text}`}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProtectRoute(ClassifyPage);
