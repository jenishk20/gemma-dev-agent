<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\User;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class SecretController extends Controller
{
    public function register(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email|unique:users',
            'username' => 'required|string|unique:users',
            'password' => 'required|string|min:6',
        ]);

        User::create([
            'email' => $request->email,
            'username' => $request->username,
            'password' => Hash::make($request->password),
        ]);

        return response()->json(['message' => 'Registration successful'], 201);
    }

    public function login(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email',
            'password' => 'required',
        ]);

        $user = User::where('email', $request->email)->first();

        if (!$user || !Hash::check($request->password, $user->password)) {
            return response()->json(['message' => 'Invalid email or password'], 401);
        }

        $token = Str::random(60);
        $user->update(['token' => $token]);

        return response()->json([
            'token' => $token,
            'message' => 'Login successful'
        ], 200);
    }

    public function setSecret(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'secret' => 'required|string',
        ]);

        $user = $request->user();
        
        if (!$user || $user->username !== $request->username) {
            return response()->json(['message' => 'Unauthorized access to this username'], 401);
        }

        $user->update(['secret' => $request->secret]);

        return response()->json(['message' => 'Secret has been set successfully'], 200);
    }

    public function getSecret(Request $request)
    {
        $username = $request->query('username');
        if (!$username) {
            return response()->json(['message' => 'Username is required'], 400);
        }

        $user = $request->user();

        if (!$user || $user->username !== $username) {
            return response()->json(['message' => 'Invalid authentication token'], 401);
        }

        return response()->json(['secret' => $user->secret], 200);
    }
}