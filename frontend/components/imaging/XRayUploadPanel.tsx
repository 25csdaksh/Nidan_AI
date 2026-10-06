"use client";

import React, { useState } from "react";
import { uploadImagingStudy } from "@/lib/api";

interface XRayUploadPanelProps {
  patientId: string;
  onUploadSuccess: (studyId: string) => void;
}

export const XRayUploadPanel: React.FC<XRayUploadPanelProps> = ({
  patientId,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [modality, setModality] = useState("XRAY");
  const [bodyPart, setBodyPart] = useState("CHEST");
  const [viewPosition, setViewPosition] = useState("PA");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (selected.type.startsWith("image/")) {
        setPreviewUrl(URL.createObjectURL(selected));
      } else {
        setPreviewUrl(null);
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a valid Chest X-Ray image or DICOM file.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const study = await uploadImagingStudy(
        patientId,
        file,
        modality,
        bodyPart,
        viewPosition
      );
      onUploadSuccess(study.id);
      setFile(null);
      setPreviewUrl(null);
    } catch (err: any) {
      setError(err.message || "Upload failed. Verify image format and integrity.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl">
      <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 mb-1">
        <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        Secure Ingestion & DICOM Upload
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Supports high-resolution PNG, JPEG, and DICOM formats (up to 50MB). Patient privacy is preserved with strict PHI de-identification.
      </p>

      <form onSubmit={handleUpload} className="space-y-4">
        {/* Dropzone / File Picker */}
        <div className="border-2 border-dashed border-slate-700/80 hover:border-indigo-500/80 rounded-xl p-6 text-center transition bg-slate-950/50">
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.dcm,.dicom"
            onChange={handleFileChange}
            className="hidden"
            id="xray-file-input"
          />
          <label htmlFor="xray-file-input" className="cursor-pointer block">
            {previewUrl ? (
              <div className="flex flex-col items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-h-32 rounded-lg border border-slate-700 object-contain mb-2"
                />
                <span className="text-xs text-indigo-300 font-medium">Click to replace selected image</span>
              </div>
            ) : file ? (
              <div className="text-xs text-slate-200">
                <span className="font-semibold block text-indigo-400 mb-1">{file.name}</span>
                <span>{(file.size / (1024 * 1024)).toFixed(2)} MB · Click to change</span>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="w-10 h-10 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center mx-auto">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <p className="text-xs text-slate-300 font-medium">Drag & drop Chest X-Ray or browse files</p>
                <p className="text-[11px] text-slate-500 font-mono">PNG, JPEG, DICOM (.dcm)</p>
              </div>
            )}
          </label>
        </div>

        {/* Acquisition Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label className="block text-slate-400 mb-1 font-medium">Modality</label>
            <select
              value={modality}
              onChange={(e) => setModality(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            >
              <option value="XRAY">X-Ray (Radiography)</option>
              <option value="CT">CT (Computed Tomography)</option>
              <option value="MRI">MRI</option>
              <option value="ULTRASOUND">Ultrasound</option>
            </select>
          </div>
          <div>
            <label className="block text-slate-400 mb-1 font-medium">Anatomical Region</label>
            <input
              type="text"
              value={bodyPart}
              onChange={(e) => setBodyPart(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
              placeholder="e.g. CHEST"
            />
          </div>
          <div>
            <label className="block text-slate-400 mb-1 font-medium">View Position</label>
            <select
              value={viewPosition}
              onChange={(e) => setViewPosition(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
            >
              <option value="PA">PA (Posteroanterior)</option>
              <option value="AP">AP (Anteroposterior)</option>
              <option value="LATERAL">Lateral</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!file || isUploading}
          className="w-full py-2.5 rounded-xl font-semibold text-xs text-white bg-indigo-600 hover:bg-indigo-500 transition disabled:opacity-50 shadow-lg shadow-indigo-950/40 flex items-center justify-center gap-2"
        >
          {isUploading ? "Uploading & Validating..." : "Upload & Run Analysis"}
        </button>
      </form>
    </div>
  );
};
