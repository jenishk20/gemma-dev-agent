<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\UserProfile;
use Illuminate\Support\Facades\Response;

class ProfileController extends Controller
{
    public function addProfile(Request $request)
    {
        $this->validate($request, [
            'username' => 'required|string',
            'profile_page' => 'required|string',
            'profile_photo' => 'required|file|image|png',
        ]);

        if (UserProfile::where('username', $request->input('username'))->exists()) {
            return response('Profile already exists', 403);
        }

        $photo = $request->file('profile_photo');
        $photoData = file_get_contents($photo->getRealPath());

        try {
            UserProfile::create([
                'username' => $request->input('username'),
                'profile_page' => $request->input('profile_page'),
                'profile_photo' => $photoData,
            ]);
            return response('', 201);
        } catch (\Exception $e) {
            return response('Invalid input', 400);
        }
    }

    public function getProfile($username)
    {
        $profile = UserProfile::where('username', $username)->first();

        if (!$profile) {
            return response('Profile not found', 404);
        }

        return response($profile->profile_page, 200)->header('Content-Type', 'text/html');
    }

    public function getPhoto($username)
    {
        $profile = UserProfile::where('username', $username)->first();

        if (!$profile) {
            return response('Photo not found', 404);
        }

        return response($profile->profile_photo, 200)->header('Content-Type', 'image/png');
    }
}