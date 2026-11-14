<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\User;
use Illuminate\Support\Facades\Storage;

class ProfileController extends Controller
{
    public function addProfile(Request $request)
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
        $filename = $request->input('username') . '.png';
        
        // Store photo in storage/app/profiles
        $path = $photo->storeAs('profiles', $filename);

        User::create([
            'username' => $request->input('username'),
            'profile_page' => $request->input('profile_page'),
            'profile_photo_path' => $path,
        ]);

        return response('', 201);
    }

    public function getProfile($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user) {
            return response('Profile not found', 404);
        }

        return response($user->profile_page, 200)->header('Content-Type', 'text/html');
    }

    public function getPhoto($username)
    {
        $user = User::where('username', $username)->first();

        if (!$user || !Storage::exists($user->profile_photo_path)) {
            return response('Photo not found', 404);
        }

        return response()->file(Storage::path($user->profile_photo_path), ['Content-Type' => 'image/png']);
    }
}