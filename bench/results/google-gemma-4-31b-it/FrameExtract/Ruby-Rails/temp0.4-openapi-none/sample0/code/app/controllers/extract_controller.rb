require 'open3'

class ExtractController < ApplicationController
  def create
    video_file = params[:video]
    frame_number = params[:frameNumber]
    
    if video_file.nil? || frame_number.nil?
      return render json: { error: "Missing video or frameNumber" }, status: :bad_request
    end

    # Create temporary paths for input and output
    # We use the uploaded file's tempfile path directly
    input_path = video_file.path
    output_path = Rails.root.join('tmp', "frame_#{SecureRandom.uuid}.png").to_s

    # ffmpeg command: 
    # -i: input file
    # -vf "select='eq(n,FRAME_INDEX)'": filter to select the specific frame index
    # -vframes 1: output exactly one frame
    # -f image2: force image format
    cmd = "ffmpeg -i #{Shellwords.escape(input_path)} -vf \"select='eq(n,#{frame_number.to_i})'\" -vframes 1 -f image2 #{Shellwords.escape(output_path)}"

    stdout, stderr, status = Open3.capture3(cmd)

    if status.success? && File.exist?(output_path)
      # Send the file and ensure it's deleted after the request is finished
      send_file output_path, type: 'image/png', disposition: 'inline', expires: 0
      
      # Note: In a production app, we would use a background job or a 
      # cleanup middleware to delete the temporary PNG. 
      # For this small app, we rely on the tmp folder.
    else
      render json: { error: "Frame at index #{frame_number} could not be found." }, status: :not_found
    end
  end
end