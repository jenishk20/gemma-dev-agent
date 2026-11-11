<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\User;
use App\Models\Invitation;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Hash;

class UserController extends Controller
{
    public function inviteUser(Request $request)
    {
        $this->validate($request, [
            'email' => 'required|email',
        ]);

        $email = $request->input('email');

        // Check if invitation already exists
        $invitation = Invitation::where('email', $email)->first();

        if (!$invitation) {
            $invitation = Invitation::create([
                'email' => $email,
                'invite_id' => Str::random(40),
                'used' => false,
            ]);
        }

        return response()->json([
            'invite_id' => $invitation->invite_id,
            'message' => 'Invitation created successfully'
        ], 200);
    }

    public function createUser(Request $request)
    {
        $this->validate($request, [
            'invite_id' => 'required',
            'user_name' => 'required',
            'password' => 'required',
        ]);

        $inviteId = $request->input('invite_id');
        $userName = $request->input('user_name');
        $password = $request->input('password');

        // Validate invitation
        $invitation = Invitation::where('invite_id', $inviteId)->where('used', false)->first();

        if (!$invitation) {
            return response()->json(['message' => 'Invalid invite_id'], 401);
        }

        // Check if username exists
        if (User::where('user_name', $userName)->exists()) {
            return response()->json(['message' => 'Username already exists. Try providing different username.'], 400);
        }

        // Create user
        User::create([
            'user_name' => $userName,
            'email' => $invitation->email,
            'password' => Hash::make($password),
        ]);

        // Mark invitation as used
        $invitation->used = true;
        $invitation->save();

        return response()->json(['message' => 'User created successfully'], 200);
    }
}