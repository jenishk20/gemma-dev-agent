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

        $service = Service::where('service_id', $serviceId)->first();

        if ($service && $service->token !== $token) {
            return response()->json(['error' => 'Unauthorized'], 400);
        }

        Service::updateOrCreate(
            ['service_id' => $serviceId],
            [
                'token' => $token,
                'last_notification' => Carbon::now()
            ]
        );

        return response()->json([], 200);
    }

    public function getServices(Request $request)
    {
        $this->validate($request, [
            'token' => 'required|string',
        ]);

        $token = $request->input('token');
        $services = Service::where('token', $token)->get();

        $result = $services->map(function ($service) {
            return [
                'serviceId' => $service->service_id,
                'lastNotification' => $service->last_notification ? $service->last_notification->toDateTimeString() : null,
            ];
        });

        return response()->json($result, 200);
    }
}