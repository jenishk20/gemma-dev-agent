<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;

class UnsubscribeController extends Controller
{
    /**
     * Decide if a user wants to be unsubscribed based on raw email content.
     *
     * @param Request $request
     * @return Response
     */
    public function decide(Request $request)
    {
        // Get the raw body of the request
        $content = $request->getContent();

        if (empty($content)) {
            return response()->json(['email' => null, 'unsubscribe' => false], 200);
        }

        // 1. Extract Email Address from "From: ..." header
        // Regex looks for "From:" followed by optional name in brackets or quotes, then the email
        $email = null;
        if (preg_match('/From:.*<([^>]+)>/i', $content, $matches)) {
            $email = $matches[1];
        } elseif (preg_match('/From:\s*([^\s\r\n]+)/i', $content, $matches)) {
            $email = trim($matches[1]);
        }

        // 2. Check for unsubscribe keywords
        $keywords = [
            'unsubscribe',
            'remove me',
            'deregister me',
            'stop sending me',
            'delete me'
        ];

        $shouldUnsubscribe = false;
        $lowerContent = strtolower($content);

        foreach ($keywords as $keyword) {
            if (str_contains($lowerContent, $keyword)) {
                $shouldUnsubscribe = true;
                break;
            }
        }

        return response()->json([
            'email' => $email,
            'unsubscribe' => $shouldUnsubscribe
        ], 200);
    }
}