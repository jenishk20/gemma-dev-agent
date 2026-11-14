<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\UserProfile;
use Illuminate\Support\Facades\Storage;

class ProfileController extends Controller
{
    public function store(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'profile_page' => 'required|string',
            'profile_photo' => 'required|image|mimes:png',
        ]);

        if (UserProfile::where('username', $request->username)->exists()) {
            return response('Profile already exists', 403);
        }

        // Save HTML to DB
        $profile = UserProfile::create([
            'username' => $request->username,
            'profile_page' => $request->profile_page,
        ]);

        // Save PNG to storage
        if ($request->hasFile('profile_photo')) {
            $path = $request->file('profile_photo')->storeAs(
                'profiles', 
                $request->username . '.png'
            );
        }

        return response('Profile created successfully', 201);
    }

    public function show($username)
    {
        $profile = UserProfile::where('username', $username)->first();

        if (!$profile) {
            return response('Profile not found', 404);
        }

        return response($profile->profile_page, 200)
                ->header('Content-Type', 'text/html');
    }

    public function photo($username)
    {
        $path = 'profiles/' . $username . '.png';

        if (!Storage::exists($path)) {
            return response('Photo not found', 404);
        }

        return response()->file(storage_path('app/' . $path), 200, [
            'Content-Type' => 'image/png'
        ]);
    }
}