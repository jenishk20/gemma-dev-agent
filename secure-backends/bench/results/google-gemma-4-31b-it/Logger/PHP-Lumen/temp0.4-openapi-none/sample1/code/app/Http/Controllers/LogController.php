<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class LogController extends Controller
{
    private $logFile = 'logs.txt';

    /**
     * Log a message to the server.
     * 
     * @param Request $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request)
    {
        $this->validate($request, [
            'message' => 'required|string',
        ]);

        $message = $request->input('message');
        
        // Append the message and a newline to the file
        // storage_path() is used to ensure the file is in a writable directory
        $filePath = storage_path($this->logFile);
        file_put_contents($filePath, $message . PHP_EOL, FILE_APPEND);

        return response()->json([], 200);
    }

    /**
     * Retrieve all logged messages.
     * 
     * @return \Illuminate\Http\Response
     */
    public function index()
    {
        $filePath = storage_path($this->logFile);

        if (!File::exists($filePath)) {
            return response(' ', 200)->header('Content-Type', 'text/plain');
        }

        $content = File::get($filePath);
        
        // Return as text/plain as per OpenAPI schema
        return response($content, 200)->header('Content-Type', 'text/plain');
    }
}