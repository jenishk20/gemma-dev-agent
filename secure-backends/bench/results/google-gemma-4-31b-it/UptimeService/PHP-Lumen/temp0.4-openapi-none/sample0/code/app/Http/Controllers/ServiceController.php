<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\ServiceStatus;
use Illuminate\Support\Carbon;

class ServiceController extends Controller
{
    public function heartbeat(Request $request)
    {
        $this->validate($request, [
            'serviceId' => 'required|string',
            'token' => 'required|string',
        ]);

        $serviceId = $request->input('serviceId');
        $token = $request->input('token');

        try {
            // Update or Create the service record
            ServiceStatus::updateOrCreate(
                ['serviceId' => $serviceId],
                [
                    'token' => $token,
                    'lastNotification' => Carbon::now()->toDateTimeString()
                ]
            );

            return response()->json(['message' => 'Heartbeat registered successfully.'], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }

    public function index(Request $request)
    {
        $this->validate($request, [
            'token' => 'required|string',
        ]);

        $token = $request->input('token');

        try {
            $services = ServiceStatus::where('token', $token)
                ->get(['serviceId', 'lastNotification']);

            return response()->json($services, 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}