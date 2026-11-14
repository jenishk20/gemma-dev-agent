class MonitorController < ApplicationController
  def commands
    # Validate request body
    command_regex_str = params[:command_regex]
    filter_flags = params[:filter_flags] || ""

    if command_regex_str.blank?
      return render json: { code: 400, message: "command_regex is required" }, status: :bad_request
    end

    begin
      # Create a regex object from the input
      regex = Regexp.new(command_regex_str)
      
      # Execute ps command. 
      # We use the provided filter_flags. To prevent command injection, 
      # we strictly validate that flags only contain alphanumeric characters, spaces, and dashes.
      safe_flags = filter_flags.gsub(/[^a-zA-Z0-9\s\-]/, '')
      
      # Run ps. We use `ps #{safe_flags}`. 
      # Note: Since 'command' param isn't supported, we get the default output.
      # We use backticks to capture the stdout.
      output = `ps #{safe_flags}`
      
      processes = []
      
      # ps output typically starts with a header. We skip the first line.
      lines = output.split("\n")
      lines.shift if lines.any?

      lines.each do |line|
        # ps output format varies, but typically the first column is PID.
        # We split by whitespace to isolate the PID and the rest of the string.
        parts = line.strip.split(/\s+/, 2)
        next if parts.length < 2

        pid_str = parts[0]
        process_string = parts[1]

        # Check if the process string matches the provided regex
        if process_string =~ regex
          # Ensure PID is actually an integer
          if pid_str =~ /^\d+$/
            processes << {
              processId: pid_str.to_i,
              processString: process_string
            }
          end
        end
      end

      render json: processes, status: :ok

    rescue RegexpError => e
      render json: { code: 400, message: "Invalid regular expression: #{e.message}" }, status: :bad_request
    rescue StandardError => e
      render json: { code: 500, message: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end