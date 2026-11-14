<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Symfony\Component\HttpFoundation\Response;

class PdfController extends Controller
{
    public function convert(Request $request)
    {
        // Validate that the file exists and is uploaded
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        $file = $request->file('file');

        // Validate MIME type to ensure it is a PDF
        if ($file->getClientMimeType() !== 'application/pdf') {
            return response()->json(['error' => 'Invalid file type. Please upload a PDF.'], 400);
        }

        // Store file temporarily
        $tempPath = tempnam(sys_get_temp_dir(), 'pdf_');
        $file->move(dirname($tempPath), basename($tempPath));

        try {
            // pdftotext -layout extracts text while attempting to maintain visual layout
            // The '-' argument tells pdftotext to output to stdout
            $command = sprintf('pdftotext -layout %s -', escapeshellarg($tempPath));
            $output = shell_exec($command);

            if ($output === null) {
                throw new \Exception('Failed to extract text from PDF');
            }

            // Clean up temporary file
            unlink($tempPath);

            // Return as plain text as per OpenAPI spec
            return response($output, 200)
                ->header('Content-Type', 'text/plain');

        } catch (\Exception $e) {
            if (file_exists($tempPath)) {
                unlink($tempPath);
            }
            return response()->json(['error' => 'Internal Server Error - Conversion failed'], 500);
        }
    }
}