<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class ProfileController extends Controller
{
    public function store(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'profile_page' => 'required|string',
            'profile_photo' => 'required|file|image|png',
        ]);

        if (User::where('username', $request->username)->exists()) {
            return response()->json(['error' => 'Profile already exists'], 403);
        }

        $photo = $request->file('profile_photo');
        $filename = $request->username . '_photo.png';
        
        // Store file in storage/app/public/profiles
        $path = $photo->storeAs('profiles', $filename);

        $user = User::create([
            'username' => $request->username,
            'profile_page' => $request->profile_page,
            'profile_photo_path' => $path,
        ]);

        return response()->json(['message' => 'Profile created successfully'], 201);
    }

    public function show($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user) {
            return response()->json(['error' => 'Profile not found'], 404);
        }

        return response($user->profile_page, 200)->header('Content-Type', 'text/html');
    }

    public function photo($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user || !Storage::exists($user->profile_photo_path)) {
            return response()->json(['error' => 'Photo not found'], 404);
        }

        return Storage::response($user->profile_photo_path, 'image/png');
    }
}