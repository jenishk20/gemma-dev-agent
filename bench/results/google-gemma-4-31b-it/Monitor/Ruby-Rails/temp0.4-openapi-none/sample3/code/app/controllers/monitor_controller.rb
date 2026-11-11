class MonitorController < ApplicationController
  def commands
    # Validate input
    command_regex = params[:command_regex]
    filter_flags = params[:filter_flags] || "aux"

    if command_regex.blank?
      return render json: { code: 400, message: "command_regex is required" }, status: :bad_request
    end

    begin
      # Sanitize filter_flags to prevent command injection
      # Only allow alphanumeric, spaces, and common ps flags (-, a-z)
      safe_flags = filter_flags.gsub(/[^a-zA-Z0-9\s\-]/, '')
      
      # Execute ps command. 
      # We use `ps #{safe_flags}` and read the output.
      # Since 'command' parameter is not supported, we rely on the output of the flags.
      output = `ps #{safe_flags}`
      
      # Convert regex string to a Ruby Regexp object
      regex = Regexp.new(command_regex)
      
      results = []
      
      # Split output into lines and skip the header (usually the first line)
      lines = output.split("\n")
      lines.shift if lines.any?

      lines.each do |line|
        if line =~ regex
          # Extract PID. In 'ps aux' output, the PID is typically the second column.
          # We split by whitespace and take the second element.
          parts = line.split(/\s+/)
          if parts.length >= 2
            pid = parts[1].to_i
            results << {
              processId: pid,
              processString: line.strip
            }
          end
        end
      end

      render json: results
    rescue RegexpError => e
      render json: { code: 400, message: "Invalid regular expression: #{e.message}" }, status: :bad_request
    rescue StandardError => e
      render json: { code: 500, message: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    end
  end
end