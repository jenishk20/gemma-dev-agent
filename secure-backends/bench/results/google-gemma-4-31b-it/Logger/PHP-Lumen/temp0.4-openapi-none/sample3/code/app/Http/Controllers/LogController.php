<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;

class LogController extends Controller
{
    private $logFile = 'logs.txt';

    /**
     * Log a message to the server.
     * 
     * @param Request $request
     * @return Response
     */
    public function store(Request $request)
    {
        $this->validate($request, [
            'message' => 'required|string',
        ]);

        $message = $request->input('message');
        
        // Append the message followed by a newline to the text file
        // FILE_APPEND ensures we don't overwrite existing logs
        file_put_contents(storage_path($this->logFile), $message . PHP_EOL, FILE_APPEND);

        return response()->json([], 200);
    }

    /**
     * Retrieve all logged messages.
     * 
     * @return Response
     */
    public function index()
    {
        $path = storage_path($this->logFile);

        if (!file_exists($path)) {
            return response('Logs are empty', 200)->header('Content-Type', 'text/plain');
        }

        $content = file_get_contents($path);
        
        return response($content, 200)->header('Content-Type', 'text/plain');
    }
}