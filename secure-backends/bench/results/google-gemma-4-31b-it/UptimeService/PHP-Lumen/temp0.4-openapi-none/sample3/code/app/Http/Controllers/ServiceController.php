<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Service;
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

        // Update or Create the service record
        $service = Service::updateOrCreate(
            ['serviceId' => $serviceId],
            [
                'token' => $token,
                'last_notification' => Carbon::now()
            ]
        );

        return response()->json(['message' => 'Heartbeat registered successfully.'], 200);
    }

    public function getServices(Request $request)
    {
        $this->validate($request, [
            'token' => 'required|string',
        ]);

        $token = $request->input('token');

        $services = Service::where('token', $token)
            ->get(['serviceId', 'last_notification']);

        $result = $services->map(function ($service) {
            return [
                'serviceId' => $service->serviceId,
                'lastNotification' => $service->last_notification->toIso8601String(),
            ];
        });

        return response()->json($result, 200);
    }
}