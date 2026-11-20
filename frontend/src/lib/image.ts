import { uz } from '../i18n/uz';

const MAX_SIDE = 1280;
const JPEG_QUALITY = 0.85;
const MAX_INPUT_BYTES = 8 * 1024 * 1024;

export class ImageError extends Error {}

/**
 * Decode a user-picked photo, apply its EXIF orientation, shrink the longest
 * side to MAX_SIDE and re-encode as JPEG.
 *
 * Phone photos are routinely 4000px and 6+ MB, and iPhones hand over HEIC that
 * only the OS decoder understands - so decoding happens through createImageBitmap
 * (which uses the platform decoder) with an <img> fallback.
 */
export async function prepareImage(file: File): Promise<Blob> {
  if (file.size > MAX_INPUT_BYTES) {
    throw new ImageError(uz.errorImageTooLarge);
  }

  const bitmap = await decode(file);
  try {
    return await encode(bitmap);
  } finally {
    bitmap.close?.();
  }
}

type Decoded = { width: number; height: number; close?: () => void } & CanvasImageSource;

async function decode(file: File): Promise<Decoded> {
  if (typeof createImageBitmap === 'function') {
    try {
      // imageOrientation: 'from-image' applies the EXIF rotation for us.
      return (await createImageBitmap(file, {
        imageOrientation: 'from-image',
      })) as Decoded;
    } catch {
      // Fall through to the <img> path below.
    }
  }
  return decodeViaImgElement(file);
}

function decodeViaImgElement(file: File): Promise<Decoded> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();

    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(
        Object.assign(img, {
          width: img.naturalWidth,
          height: img.naturalHeight,
        }) as unknown as Decoded,
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new ImageError(uz.errorImageDecode));
    };
    img.src = url;
  });
}

async function encode(source: Decoded): Promise<Blob> {
  const { width, height } = fit(source.width, source.height);
  if (!width || !height) throw new ImageError(uz.errorImageDecode);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const context = canvas.getContext('2d');
  if (!context) throw new ImageError(uz.errorImageDecode);
  context.drawImage(source, 0, 0, width, height);

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY),
  );
  if (!blob) throw new ImageError(uz.errorImageDecode);
  return blob;
}

function fit(width: number, height: number) {
  const longest = Math.max(width, height);
  if (longest <= MAX_SIDE) return { width, height };

  const scale = MAX_SIDE / longest;
  return {
    width: Math.round(width * scale),
    height: Math.round(height * scale),
  };
}
