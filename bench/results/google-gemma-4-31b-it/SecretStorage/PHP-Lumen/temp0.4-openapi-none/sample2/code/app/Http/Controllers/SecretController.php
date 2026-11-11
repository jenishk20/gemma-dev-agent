<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\User;

class SecretController extends Controller
{
    public function setSecret(Request $request)
    {
        $this->validate($request, [
            'username' => 'required',
            'secret' => 'required|string',
        ]);

        $user = Auth::user();

        // Ensure the authenticated user is the one setting the secret for their own username
        if ($user->username !== $request->username) {
            return response()->json(['message' => 'Unauthorized'], 401);
        }

        $user->secret = $request->secret;
        $user->save();

        return response()->json(['message' => 'Secret has been set successfully'], 200);
    }

    public function getSecret(Request $request)
    {
        $this->validate($request, [
            'username' => 'required',
        ]);

        $user = Auth::user();

        if (!$user || $user->username !== $request->username) {
            return response()->json(['message' => 'Invalid authentication token'], 401);
        }

        return response()->json([
            'secret' => $user->secret
        ], 200);
    }
}