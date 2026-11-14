<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Response;

class ProfileController extends Controller
{
    public function store(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'profile_page' => 'required|string',
            'profile_photo' => 'required|file|image|png',
        ]);

        if (User::where('username', $request->input('username'))->exists()) {
            return response('Profile already exists', 403);
        }

        $photo = $request->file('profile_photo');
        $photoData = file_get_contents($photo->getRealPath());

        $user = User::create([
            'username' => $request->input('username'),
            'profile_page' => $request->input('profile_page'),
            'profile_photo' => $photoData,
        ]);

        return response()->json(['message' => 'Profile created successfully'], 201);
    }

    public function show($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user) {
            return response('Profile not found', 404);
        }

        return response($user->profile_page, 200)
            ->header('Content-Type', 'text/html');
    }

    public function photo($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user) {
            return response('Photo not found', 404);
        }

        return response($user->profile_photo, 200)
            ->header('Content-Type', 'image/png');
    }
}