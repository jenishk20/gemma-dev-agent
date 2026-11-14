<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpFoundation\Response;

class PdfController extends Controller
{
    /**
     * Convert PDF file to text using pdftotext utility.
     *
     * @param Request $request
     * @return \Illuminate\Http\Response
     */
    public function convert(Request $request)
    {
        // 1. Validation: Check if file exists in request
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        $file = $request->file('file');

        // 2. Validation: Check if it is actually a PDF
        if ($file->getClientOriginalExtension() !== 'pdf' && $file->getMimeType() !== 'application/pdf') {
            return response()->json(['error' => 'Invalid file format. Please upload a PDF.'], 400);
        }

        try {
            // Store file temporarily to process it
            $tempPath = $file->getRealPath();

            // Execute pdftotext. 
            // '-' tells pdftotext to send output to stdout.
            // escapeshellarg ensures the filename is safe from shell injection.
            $command = "pdftotext " . escapeshellarg($tempPath) . " -";
            
            $output = [];
            $resultCode = 0;
            exec($command, $output, $resultCode);

            if ($resultCode !== 0) {
                throw new \Exception("pdftotext failed to process the file.");
            }

            // Join the array of lines into a single plain text string
            $text = implode("\n", $output);

            // Return as plain text as per OpenAPI spec
            return response($text, 200)
                ->header('Content-Type', 'text/plain');

        } catch (\Exception $e) {
            Log::error("PDF Conversion Error: " . $e->getMessage());
            return response()->json(['error' => 'Internal Server Error - Conversion failed'], 500);
        }
    }
}