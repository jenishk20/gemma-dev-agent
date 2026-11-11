import { Controller, Get, Post, Put, Body, Param, Res, HttpStatus } from '@nestjs/common';
import { AppService, NewEntry, UpdateEntry } from './app.service';
import { Response } from 'express';

@Controller('entries')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async list(@Res() res: Response) {
    const entries = await this.appService.getAllEntries();
    let html = '<h1>Wiki Entries</h1><ul>';
    entries.forEach(e => {
      html += `<li><a href="/entries/${e.id}">${e.title}</a></li>`;
    });
    html += '</ul><hr><a href="/create">Create New Entry</a>'; // Helper link for testing
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Post()
  async create(@Body() body: NewEntry) {
    return await this.appService.createEntry(body);
  }

  @Get(':entryId')
  async get(@Param('entryId') id: string, @Res() res: Response) {
    const entry = await this.appService.getEntry(id);
    const html = `
      <h1>${entry.title}</h1>
      <p>${entry.content}</p>
      <hr>
      <p>Last modified by: ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</p>
      <a href="/entries/${id}/edits">View History</a> | <a href="/entries">Back to List</a>
    `;
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Put(':entryId')
  async update(@Param('entryId') id: string, @Body() body: UpdateEntry) {
    return await this.appService.updateEntry(id, body);
  }

  @Get(':entryId/edits')
  async history(@Param('entryId') id: string, @Res() res: Response) {
    const { entry, edits } = await this.appService.getEdits(id);
    let html = `<h1>Edit History for ${entry.title}</h1><ul>`;
    
    for (let i = 0; i < edits.length; i++) {
      const edit = edits[i];
      const prev = edits[i + 1];
      const diff = prev ? ` <br><i>Changed from: ${prev.content}</i>` : ' (Initial Version)';
      
      html += `<li>
        <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt})<br>
        Summary: ${edit.summary}<br>
        Content: ${edit.content} ${diff}
      </li><br>`;
    }
    
    html += '</ul><a href="/entries/' + id + '">Back to Entry</a>';
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }
}