// ============================================================
// Upload.jsx
// ============================================================
// This is the first step — the drag and drop upload screen.
// The user drags their screenshots here and we send them
// to our FastAPI backend which runs the AI on them.
//
// We use react-dropzone to handle the drag and drop.
// It gives us a lot of functionality for free like:
// - Highlighting the drop zone when you drag a file over it
// - Accepting only image files
// - Handling multiple files at once
// ============================================================

import { useState, useCallback } from "react";
// useState — store data that changes (files list, loading state)
// useCallback — optimizes functions so they don't get recreated
//               every single render. Important for dropzone.

import { useDropzone } from "react-dropzone";
// useDropzone is the main hook from react-dropzone.
// A "hook" is a special React function that adds functionality.

import axios from "axios";
// axios sends HTTP requests to our FastAPI backend.
// Think of it like fetch() but easier to use.

import { Upload as UploadIcon, X, ImageIcon, Loader } from "lucide-react";
// Icons we'll use in this component.
// We rename "Upload" to "UploadIcon" because our component
// is also called Upload and names can't clash.

import "./Upload.css";

function Upload({ onUploadComplete }) {
  // --------------------------------------------------------
  // "onUploadComplete" is a prop passed from Home.jsx.
  // It's the function we call when AI finishes processing.
  // Props are how parent components talk to child components.
  // --------------------------------------------------------

  const [files, setFiles] = useState([]);
  // List of files the user has dropped/selected

  const [loading, setLoading] = useState(false);
  // True when we're sending files to the backend and waiting

  const [error, setError] = useState(null);
  // Stores any error message to show the user

  const onDrop = useCallback((acceptedFiles) => {
    // --------------------------------------------------------
    // This function runs whenever files are dropped.
    // "acceptedFiles" is the list of files that were dropped.
    // useCallback makes sure this function doesn't get
    // recreated on every render which would break dropzone.
    // --------------------------------------------------------
    setError(null);
    // Clear any previous errors

    setFiles((prev) => [...prev, ...acceptedFiles]);
    // Add new files to existing files list.
    // "..." is the spread operator — it expands the array.
    // [...prev, ...acceptedFiles] means "old files + new files"
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    // Only accept image files (png, jpg, etc.)
    multiple: true,
    // Allow multiple files at once
  });
  // getRootProps — props to put on the drop zone div
  // getInputProps — props for the hidden file input
  // isDragActive — true when user is dragging a file over the zone

  const removeFile = (index) => {
    // Remove a file from the list by its index
    setFiles((prev) => prev.filter((_, i) => i !== index));
    // filter keeps all files EXCEPT the one at the given index
  };

  const handleSubmit = async () => {
    // --------------------------------------------------------
    // This function runs when the user clicks "Analyze Schedule"
    // It sends all the files to our FastAPI backend.
    // "async" means it can wait for the server response.
    // --------------------------------------------------------

    if (files.length === 0) {
      setError("Please upload at least one screenshot first!");
      return;
      // Don't proceed if no files uploaded
    }

    setLoading(true);
    setError(null);
    // Show loading state and clear errors

    try {
      const formData = new FormData();
      // FormData is the standard way to send files over HTTP.
      // It's like packing files into an envelope to mail them.

      files.forEach((file) => {
        formData.append("files", file);
        // Add each file to the form data envelope.
        // "files" must match the parameter name in our FastAPI endpoint.
      });

      const response = await axios.post(
        "http://localhost:8000/upload",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          // Tell the server we're sending files not JSON
        }
      );
      // "await" pauses here until the server responds.
      // axios.post sends a POST request to our backend.

      onUploadComplete(response.data.events);
      // Call the function from Home.jsx with the events we got back.
      // This moves the user to step 2 automatically.

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Something went wrong. Make sure the backend is running!"
      );
      // Show the error message from the server if available.
      // "?." is optional chaining — prevents crashes if response is null.
    } finally {
      setLoading(false);
      // Always turn off loading spinner whether success or error
    }
  };

  return (
    <div className="upload-container">

      {/* Header */}
      <div className="upload-header">
        <h1 className="upload-title">Upload Your Schedule</h1>
        <p className="upload-subtitle">
          Drop in screenshots of your class schedule, syllabus, or
          semester calendar. Our AI will extract all your events automatically.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? "dropzone-active" : ""}`}
      >
        {/* {...getRootProps()} spreads all the dropzone props onto this div
            isDragActive changes the style when dragging a file over */}

        <input {...getInputProps()} />
        {/* Hidden file input — dropzone manages this automatically */}

        <UploadIcon size={40} color="#6366f1" />

        {isDragActive ? (
          <p className="dropzone-text">Drop your screenshots here!</p>
        ) : (
          <p className="dropzone-text">
            Drag and drop screenshots here, or click to select files
          </p>
        )}

        <p className="dropzone-hint">
          Supports PNG, JPG, JPEG — upload multiple at once
        </p>
      </div>

      {/* File List — shows files that have been added */}
      {files.length > 0 && (
        <div className="file-list">
          <p className="file-list-title">{files.length} file(s) ready:</p>

          {files.map((file, index) => (
            <div key={index} className="file-item">
              {/* key={index} is required by React when rendering lists.
                  It helps React track which items changed. */}

              <ImageIcon size={16} color="#6366f1" />
              <span className="file-name">{file.name}</span>
              <span className="file-size">
                {(file.size / 1024).toFixed(1)} KB
                {/* Convert bytes to KB and round to 1 decimal */}
              </span>

              <button
                className="file-remove"
                onClick={() => removeFile(index)}
              >
                <X size={14} />
                {/* X button to remove this file from the list */}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="upload-error">
          {error}
        </div>
      )}

      {/* Submit button */}
      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={loading || files.length === 0}
      >
        {loading ? (
          <>
            <Loader size={16} className="spinner" />
            Analyzing your schedule...
          </>
        ) : (
          "Analyze Schedule ✨"
        )}
      </button>

      {loading && (
        <p className="upload-loading-hint">
          This may take 10-20 seconds depending on how many screenshots you uploaded.
        </p>
      )}

    </div>
  );
}

export default Upload;