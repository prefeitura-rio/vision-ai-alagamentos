"use client";

import React, { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { Spinner } from "@/components/Spinner"; // You need to create this Spinner component

import ProtectRoute from "@/components/ProtectRoute";
import api from "@/utils/api";

const ClassifyPage = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [images, setImages] = useState<any[]>([]);
  const [objects, setObjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [imageLoading, setImageLoading] = useState(true); // New state for image loading
  const [options, setOptions] = useState<string[]>([]);

  // Dummy data for title and subtitle
  const [title, setTitle] = useState("Is the image clear and sharp?");
  const [subtitle, setSubtitle] = useState(
    "Make sure all objects are identifiable.",
  );

  useEffect(() => {
    const loadImages = async () => {
      const allImages = await api.get_all_pages("/identifications/ai", 100);
      setImages(allImages);
      setLoading(false);
      setOptions(["Option 1", "Option 2", "Option 3"]); // Replace with your options
    };

    loadImages();
  }, []);

  useEffect(() => {
    const loadObjects = async () => {
      const objects = await api.get_all_pages("/objects", 100);
      setObjects(objects);
      console.log(objects);
      // TODO: continue from here
    };

    loadObjects();
  }, []);

  const handleClassify = (imageId: string, label: string) => {
    if (currentIndex < images.length - 1) {
      // If the URL of the next image is not the same as the current one, set image loading state to true
      if (
        images[currentIndex + 1].snapshot.image_url !==
        images[currentIndex].snapshot.image_url
      ) {
        setImageLoading(true);
      }
      setCurrentIndex(currentIndex + 1);
    } else {
      console.log("No more images to classify");
    }
  };

  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      const keyOptions = { "1": options[0], "2": options[1], "3": options[2] };
      const label = keyOptions[event.key];
      if (label) {
        handleClassify(images[currentIndex].id, label);
      }
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
        <p className="text-center">{`Imagem: ${currentIndex + 1} de ${
          images.length
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
              key={option}
              className="px-4 py-2 bg-blue-500 text-white rounded shadow mb-2"
              onClick={() => handleClassify(imageToClassify.id, option)}
              disabled={imageLoading} // Disable button while image is loading
            >
              {`${index + 1}. ${option}`}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProtectRoute(ClassifyPage);
