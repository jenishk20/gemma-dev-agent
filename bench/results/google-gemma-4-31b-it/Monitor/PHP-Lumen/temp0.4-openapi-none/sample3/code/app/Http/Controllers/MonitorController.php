<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class MonitorController extends Controller
{
    /**
     * Retrieve a list of running processes matching a regex.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function getProcesses(Request $request): JsonResponse
    {
        // Validate request body based on OpenAPI schema
        $this->validate($request, [
            'command_regex' => 'required|string',
            'filter_flags' => 'string',
        ]);

        $regex = $request->input('command_regex');
        $flags = $request->input('filter_flags', 'aux');

        // Sanitize flags to prevent command injection
        // Only allow alphanumeric, spaces, and dashes
        $safeFlags = preg_replace('/[^a-zA-Z0-9\s-]/', '', $flags);
        
        // Execute ps command. 
        // We use escapeshellcmd for the base command and manually sanitize flags.
        $command = "ps " . $safeFlags;
        $output = shell_exec($command);

        if ($output === null) {
            return response()->json([
                'code' => 500,
                'message' => 'Failed to execute ps command'
            ], 500);
        }

        $lines = explode("\n", trim($output));
        
        // Remove the header line (first line of ps aux)
        $header = array_shift($lines);
        
        $results = [];

        foreach ($lines as $line) {
            if (empty($line)) continue;

            // ps aux output format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
            // We split by whitespace. The first few columns are metadata, the rest is the command.
            $parts = preg_split('/\s+/', trim($line));
            
            if (count($parts) < 11) continue;

            $pid = (int)$parts[1];
            // Reconstruct the full command string (everything from the 11th column onwards)
            $processString = implode(' ', array_slice($parts, 10));

            // Filter by regular expression
            if (preg_match('/' . $regex . '/', $processString)) {
                $results[] = [
                    'processId' => $pid,
                    'processString' => $processString
                ];
            }
        }

        return response()->json($results, 200);
    }
}